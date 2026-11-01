"""v0.391 JOURNEYS (web Step 1, "Hoola tests the site itself before she sees it"): a real Chromium walks the paths a
visitor takes on the built copy, on a phone-size screen, with the site's own scripts running:

  menu   - open the phone menu, tap a page, the page opens with its heading
  form   - fill the enquiry form and send it; the thank-you line appears
  shop   - add the first product, open the cart, go to checkout, fill it, send the order; the order number appears
  blog   - open the blog, tap the first post, it opens
  lang   - tap the language switch; the page comes back in the other language

Nothing reaches her real data: the shop and form addresses are answered by a stand-in inside the browser (the same
JSON shapes Hoola's API sends), every other outside request is refused. A journey that fails is tried once more; a
second failure goes on the report (shop / form / menu = blocking, so a site whose checkout is broken cannot go live;
blog / lang = warnings). Pages run with the same file server as the checks (checks._serve)."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from . import checks as C

log = logging.getLogger("santosh.site")
BLOCKING = {"menu", "form", "shop"}
PHONE = {"width": 390, "height": 844}


def _fake_order(body: dict[str, Any], products: dict[str, dict]) -> dict[str, Any]:
    items = []
    for it in body.get("items") or []:
        p = products.get(str(it.get("slug"))) or {}
        items.append({"title": p.get("title", it.get("slug")), "unit": p.get("unit", ""), "qty": it.get("qty", 1),
                      "amount": p.get("price_text", "₹0")})
    return {"number": "O-CHECK", "token": "check", "status": "new", "status_text": "Naya order", "items": items,
            "subtotal": "₹1", "delivery": "₹0", "total": "₹1", "method": body.get("method") or "cod", "utr_told": False}


def _router(out: Path, site: dict[str, Any], seen: dict[str, Any]):
    shop = site.get("shop") or {}
    api = (shop.get("api") or "").rstrip("/")
    if api.startswith("/"):                         # no public address set (tests / a fresh server): same origin
        api = C.ORIGIN + api
    products = {p["slug"]: p for p in shop.get("products") or []}
    serve = C._serve(out, {})

    def handler(route):
        req = route.request
        url = req.url
        if api and url.startswith(api):
            path = url[len(api):].split("?")[0]
            if path == "/products":
                return route.fulfill(status=200, content_type="application/json",
                                     body=json.dumps({"products": list(products.values())}))
            if path == "/order" and req.method == "POST":
                body = json.loads(req.post_data or "{}")
                seen["order"] = body
                return route.fulfill(status=200, content_type="application/json", body=json.dumps(_fake_order(body, products)))
            return route.fulfill(status=200, content_type="application/json", body="{}")
        if req.method == "POST" and "/api/" in url:                 # the enquiry form endpoint
            seen.setdefault("posts", []).append(url)
            return route.fulfill(status=200, content_type="application/json", body='{"ok": true}')
        if url.startswith(C.ORIGIN):
            return serve(route)
        return route.abort()
    return handler


def _pages_with(out: Path, needle: str) -> list[str]:
    hits = []
    for f in sorted(out.rglob("index.html")):
        rel = f.parent.relative_to(out).as_posix()
        if len(rel.split("/")[0]) <= 8 and (out / rel.split("/")[0] / "assets").exists() and rel != ".":
            continue                                              # another language copy: the main language is enough
        if needle in f.read_text(encoding="utf-8", errors="ignore"):
            hits.append("" if rel == "." else rel + "/")
    return hits


def _menu(page) -> str:
    page.goto(C.ORIGIN + "/", wait_until="load")
    btn = page.locator(".hs-menu")
    if not btn.count() or not btn.first.is_visible():
        return "skip"
    btn.first.click()
    page.wait_for_function("document.documentElement.classList.contains('hs-open')", timeout=4000)
    links = page.locator(".hs-links a")
    target = None
    for i in range(min(links.count(), 8)):
        href = links.nth(i).get_attribute("href") or ""
        if href and href not in ("./", "#") and links.nth(i).is_visible():
            target = links.nth(i)
            break
    if target is None:
        return "no page link in the phone menu"
    href = target.get_attribute("href")
    target.click()
    page.wait_for_load_state("load")
    if page.url.rstrip("/") == (C.ORIGIN + "/").rstrip("/"):
        return f"tapping '{href}' in the phone menu did not open the page"
    if page.locator("h1").count() < 1:
        return f"the page '{href}' opened without a heading"
    return ""


def _form(page, path: str, seen: dict[str, Any]) -> str:
    page.goto(f"{C.ORIGIN}/{path}", wait_until="load")
    f = page.locator("form[data-hoola-form]:not([data-hoola-book])").first
    f.scroll_into_view_if_needed()
    for el in f.locator("input, textarea, select").all():
        typ = (el.get_attribute("type") or "text").lower()
        name = (el.get_attribute("name") or "").lower()
        if typ in ("hidden", "submit", "button") or "hp" in (el.get_attribute("class") or "").split():
            continue
        if typ in ("checkbox", "radio"):
            if el.get_attribute("required") is not None:
                el.check()
            continue
        if el.evaluate("e => e.tagName") == "SELECT":
            opts = el.locator("option").all()
            if len(opts) > 1:
                el.select_option(index=1)
            continue
        if not el.is_visible():
            continue
        val = ("9876543210" if typ == "tel" or "phone" in name or "mobile" in name else "check@example.com" if typ == "email"
               else "2026-12-01" if typ == "date" else "5" if typ == "number" else "Hoola check")
        el.fill(val)
    f.locator("[type=submit]").first.click()
    try:
        page.wait_for_selector("form[data-hoola-form]:not([data-hoola-book]) .hs-form-msg.ok", timeout=6000)
    except Exception:
        msg = f.locator(".hs-form-msg").first.text_content() if f.locator(".hs-form-msg").count() else ""
        return f"the enquiry form on '/{path}' did not send ({(msg or 'no message shown').strip()[:80]})"
    return "" if seen.get("posts") else f"the enquiry form on '/{path}' showed thanks without sending"


def _shop(page, seen: dict[str, Any]) -> str:
    page.goto(C.ORIGIN + "/shop/", wait_until="load")
    buy = page.locator("[data-hoola-buy]:not([disabled])")
    try:
        buy.first.wait_for(timeout=5000)
    except Exception:
        return "the shop page has no Add to cart button"
    page.wait_for_timeout(400)                                  # the product list arrives from the (stand-in) API
    buy.first.click()
    try:
        page.wait_for_function("(document.querySelector('.hs-cart-b b')||{}).textContent==='1'", timeout=4000)
    except Exception:
        return "Add to cart did not put the product in the cart"
    page.locator(".hs-cart-b").click()
    page.get_by_role("button", name=re.compile("Aage badhein")).click()
    form = page.locator("form.hs-checkout")
    form.wait_for(timeout=4000)
    form.locator("[name=name]").fill("Hoola Check")
    form.locator("[name=phone]").fill("9876543210")
    if form.locator("[name=address]").is_visible():
        form.locator("[name=address]").fill("12 Station Road, Akot")
        form.locator("[name=pincode]").fill("444101")
    if form.locator("[name=method]").count() == 0:
        return "checkout has no way to pay (turn on UPI or cash on delivery)"
    form.locator("[type=submit]").click()
    try:
        page.get_by_text("Order O-CHECK").wait_for(timeout=6000)
    except Exception:
        msg = form.locator(".hs-form-msg").text_content() if form.count() else ""
        return f"checkout did not finish the order ({(msg or 'no message').strip()[:80]})"
    sent = seen.get("order") or {}
    if not sent.get("items") or sent.get("phone") != "9876543210":
        return "the order sent to the server was incomplete"
    return ""


def _blog(page) -> str:
    page.goto(C.ORIGIN + "/blog/", wait_until="load")
    link = page.locator(".hs-post h3 a").first
    if not link.count():
        return "the blog page lists no posts"
    title = (link.text_content() or "").strip()
    link.click()
    page.wait_for_load_state("load")
    h1 = (page.locator("h1").first.text_content() or "").strip() if page.locator("h1").count() else ""
    return "" if h1 and h1 == title else f"the blog post '{title[:40]}' did not open"


def _lang(page) -> str:
    page.goto(C.ORIGIN + "/", wait_until="load")
    before = page.evaluate("document.documentElement.lang")
    link = page.locator("a.hs-lang").first
    if not link.count():
        menu = page.locator("details.hs-langs summary")
        if not menu.count():
            return "skip"
        menu.first.click()
        link = page.locator("details.hs-langs a:not([aria-current])").first
    link.click()
    page.wait_for_load_state("load")
    after = page.evaluate("document.documentElement.lang")
    return "" if after and after != before else "the language switch did not open the other language"


def run(out: Path, site: dict[str, Any]) -> dict[str, Any]:
    """Every journey this site has, each tried at most twice. {journeys: [{name, ok, detail}], blocking, warnings}."""
    if C.available():
        return {"journeys": [], "blocking": [], "warnings": [{"kind": "journey", "text": "journeys skipped: no Chromium",
                                                              "sections": []}]}
    from playwright.sync_api import sync_playwright
    todo: list[tuple[str, Any]] = [("menu", None)]
    forms = _pages_with(out, "data-hoola-form")
    if forms:
        todo.append(("form", forms[0]))
    if (out / "shop" / "index.html").exists() and (site.get("shop") or {}).get("api"):
        todo.append(("shop", None))
    if (out / "blog" / "index.html").exists():
        todo.append(("blog", None))
    home = (out / "index.html").read_text(errors="ignore") if (out / "index.html").exists() else ""
    if 'class="hs-lang"' in home or 'class="hs-langs"' in home:
        todo.append(("lang", None))
    result: dict[str, Any] = {"journeys": [], "blocking": [], "warnings": []}
    with sync_playwright() as p:
        b = C._launch(p)
        try:
            for name, arg in todo:
                detail = ""
                for attempt in (1, 2):
                    seen: dict[str, Any] = {}
                    errors: list[str] = []
                    ctx = b.new_context(viewport=PHONE, device_scale_factor=1)
                    page = ctx.new_page()
                    page.set_default_timeout(8000)
                    page.on("pageerror", lambda e, errors=errors: errors.append(str(e)[:160]))
                    page.route("**/*", _router(out, site, seen))
                    try:
                        detail = {"menu": lambda: _menu(page), "form": lambda: _form(page, arg, seen),
                                  "shop": lambda: _shop(page, seen), "blog": lambda: _blog(page),
                                  "lang": lambda: _lang(page)}[name]()
                    except Exception as e:
                        detail = f"{name}: {str(e).splitlines()[0][:160]}"
                    if not detail and errors:
                        detail = f"script error during the {name} journey: {errors[0]}"
                    ctx.close()
                    if not detail or detail == "skip":
                        break
                if detail == "skip":
                    continue
                result["journeys"].append({"name": name, "ok": not detail, "detail": detail})
                if detail:
                    item = {"kind": "journey", "text": f"Visitor test failed: {detail}", "sections": []}
                    (result["blocking"] if name in BLOCKING else result["warnings"]).append(item)
        finally:
            b.close()
    return result

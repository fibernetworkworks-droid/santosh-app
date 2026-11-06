"""v0.617 KUCHH NA CHHOOTE - after a change in her words, did the site keep what it carried? (the idea of Hallmark's
redesign `--before / --kept` sweep, Nutlope/hallmark MIT, re-written in Hoola's own Python; docs/research/hallmark/).

When she asks for a change, Opus rewrites the sections the change touches. A rewrite can quietly drop her phone link,
her WhatsApp button, an enquiry form, a field of that form, a page link, or a live piece Hoola wires in (the shop's
products, her blog posts, a chart, a booking picker). Nothing used to compare. Now the previous version's built files
and the new ones are read the same way, and what went missing is NAMED:

- only for a change in her words (`_run_build` with `only`), never the first build;
- what she asked to remove is not reported (her words name it: 'phone number hatao', 'remove the form'...);
- it never blocks a launch and never edits anything by itself - the version report carries `kept.lost`, a warning per
  item, and one line in her chat so she can say 'wapas lagao'."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

HREF = re.compile(r"""<a\b[^>]*\bhref\s*=\s*["']([^"']+)["']""", re.I)
FORM = re.compile(r"<form\b([^>]*)>(.*?)</form>", re.I | re.S)
FIELD = re.compile(r"""<(?:input|select|textarea)\b[^>]*\bname\s*=\s*["']([\w\-\[\]]+)["']""", re.I)
HOOK = re.compile(r"""\b(data-hoola-(?:form|posts|product|chart|img|quiz|config|compare-table|lottie|hero3d|slots|booking|map|youtube|pay|cart|queue))(?:\s*=\s*["']([^"']*)["'])?""", re.I)
REMOVE = re.compile(r"\b(hata\w*|hatao|nikal\w*|remove\w*|delete\w*|band\s+kar\w*|mat\s+dikha\w*|no\s+more|without|bina)\b", re.I)
KIND_WORDS = {"phone": ("phone", "call", "number", "nambar", "tel", "fone"),
              "whatsapp": ("whatsapp", "wa ", "watsapp", "whats app"),
              "email": ("email", "mail"),
              "form": ("form", "enquiry", "inquiry", "contact"),
              "field": ("field", "form", "box"),
              "page": ("page", "link", "menu"),
              "hook": ("shop", "product", "blog", "post", "chart", "photo", "picture", "quiz", "map", "video",
                       "booking", "slot", "animation", "3d", "cart", "pay", "queue")}
HOOK_NAMES = {"data-hoola-form": "enquiry form", "data-hoola-posts": "her blog posts", "data-hoola-product": "a shop product",
              "data-hoola-chart": "a chart", "data-hoola-img": "a photo", "data-hoola-quiz": "a quiz",
              "data-hoola-config": "a configurator", "data-hoola-compare-table": "a comparison table",
              "data-hoola-lottie": "an animation", "data-hoola-hero3d": "the 3D hero", "data-hoola-slots": "booking slots",
              "data-hoola-booking": "booking", "data-hoola-map": "the map", "data-hoola-youtube": "a video",
              "data-hoola-pay": "the pay button", "data-hoola-cart": "the cart", "data-hoola-queue": "the queue"}


def _pages(out: Path) -> list[Path]:
    if not out or not out.exists():
        return []
    return [p for p in sorted(out.rglob("*.html")) if p.is_file() and p.name != "404.html"][:3000]


def signature(out: Path) -> dict[str, Any]:
    """What the built site carries: contact actions, forms + their fields, page links, wired pieces."""
    sig: dict[str, Any] = {"phone": set(), "whatsapp": set(), "email": set(), "page": set(), "form": {}, "field": set(),
                           "hook": {}, "pages": set()}
    for p in _pages(out):
        rel = p.relative_to(out).as_posix()
        sig["pages"].add(rel)
        h = p.read_text(encoding="utf-8", errors="ignore")
        for href in HREF.findall(h):
            u = href.strip()
            low = u.lower()
            if low.startswith("tel:"):                     # contact actions are kept PER PAGE: the hero's call button
                sig["phone"].add((rel, re.sub(r"[^\d+]", "", u[4:])))   # can go while the footer's stays
            elif "wa.me/" in low or "api.whatsapp.com" in low:
                m = re.search(r"(?:wa\.me/|phone=)(\d{6,15})", low)
                sig["whatsapp"].add((rel, m.group(1) if m else "whatsapp"))
            elif low.startswith("mailto:"):
                sig["email"].add((rel, low[7:].split("?")[0]))
            elif not re.match(r"^[a-z][a-z0-9+.-]*:", low) and not low.startswith(("#", "//")):
                tgt = re.sub(r"(^(\.\./)+|^\./|index\.html$|#.*$|\?.*$)", "", u).strip("/")
                if tgt and not tgt.startswith("assets/"):
                    sig["page"].add(tgt)
        forms = FORM.findall(h)
        if forms:
            sig["form"][rel] = len(forms)
            for attrs, inner in forms:
                for n in FIELD.findall(inner):
                    if n not in ("website",):                    # the honeypot is Hoola's own
                        sig["field"].add(n)
        for name, val in HOOK.findall(h):
            key = name.lower() + (f"={val}" if val and name.lower() not in ("data-hoola-img", "data-hoola-form") else "")
            sig["hook"][key] = sig["hook"].get(key, 0) + 1
    return sig


def _asked(kind: str, words: str, what: str = "") -> bool:
    """Her words asked for it to go: a removal word AND the kind (or the very field / page she named)."""
    w = f" {words.lower()} "
    if not REMOVE.search(w):
        return False
    named = bool(what) and len(what) >= 3 and what.lower().split("/")[0] in w
    return named or any(k in w for k in KIND_WORDS.get(kind, ()))


def compare(old: dict[str, Any], new: dict[str, Any], words: str = "") -> list[dict[str, str]]:
    """What the old version carried that the new one does not (her asked removals left out)."""
    lost: list[dict[str, str]] = []

    def add(kind: str, what: str, say: str) -> None:
        if not _asked(kind, words, what):
            lost.append({"kind": kind, "what": what, "say": say})

    alive = new["pages"]
    for pg, v in sorted(old["phone"] - new["phone"]):
        if pg in alive:
            add("phone", v, f"phone call link {v} ({pg})")
    for pg, v in sorted(old["whatsapp"] - new["whatsapp"]):
        if pg in alive:
            add("whatsapp", v, (f"WhatsApp button {v}" if v != "whatsapp" else "WhatsApp button") + f" ({pg})")
    for pg, v in sorted(old["email"] - new["email"]):
        if pg in alive:
            add("email", v, f"email link {v} ({pg})")
    for page, n in sorted(old["form"].items()):
        if page in new["pages"] and new["form"].get(page, 0) < n:
            add("form", page, f"a form on {page}")
    for v in sorted(old["field"] - new["field"]):
        add("field", v, f"form field '{v}'")
    gone_pages = old["pages"] - new["pages"]
    for v in sorted(old["page"] - new["page"]):
        if not any(v and v in g for g in gone_pages):          # a page that itself went away is the plan's change
            add("page", v, f"link to {v}")
    for k, n in sorted(old["hook"].items()):
        if new["hook"].get(k, 0) < n:
            base = k.split("=", 1)[0]
            label = HOOK_NAMES.get(base, base)
            add("hook", k, f"{label}" + (f" ({k.split('=', 1)[1]})" if "=" in k else "")
                + (f", {n - new['hook'].get(k, 0)} fewer" if n > 1 else ""))
    return lost[:40]


def check(old_dir: Path, new_dir: Path, words: str = "") -> dict[str, Any]:
    if not _pages(old_dir):
        return {"checked": False, "lost": [], "why": "no earlier version to compare"}
    lost = compare(signature(old_dir), signature(new_dir), words)
    return {"checked": True, "lost": lost}


def say_line(lost: list[dict[str, str]]) -> str:
    if not lost:
        return ""
    items = ", ".join(x["say"] for x in lost[:5]) + (f" aur {len(lost) - 5} aur" if len(lost) > 5 else "")
    return (f"Dhyan dijiye: is badlav ke baad yeh cheezein website par nahi mili - {items}. "
            "Galti se hata ho to bolie 'wapas lagao'; aapne khud kaha tha to theek hai.")

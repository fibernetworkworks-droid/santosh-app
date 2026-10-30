"""v0.293 Website editing like Lovable (web design Phase 2): she clicks a thing in the preview and changes it herself -
words, a link, a picture, or removes it - with no AI call, no cost and no waiting for Opus; every change can be undone.

Every element she may edit carries `data-e="<n>"` inside its section's source html (numbered once per section, kept
across edits). The preview in edit mode (`/api/site-preview/<token>/__edit/...`) loads `assets/hoola-edit.js`, which
outlines those elements, makes text editable in place and tells the console / phone what she changed
(postMessage, or the phone's `HoolaEdit` JavaScript channel). The live site never carries `data-e` (stripped on
publish, in every export and in the version copies she rolls back to)."""
from __future__ import annotations

import re
from typing import Any

TEXT_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "a", "button", "figcaption", "blockquote", "dt", "dd", "th",
             "td", "label", "small", "strong", "em", "span", "summary", "cite", "q")
KEEP_INSIDE = ("i", "svg", "img", "picture", "br")      # an icon / a picture inside a button or a heading stays put
MAX_TEXT = 1200
EDIT_ATTR = re.compile(r'\sdata-e="\d+"')


class EditError(Exception):
    pass


def _soup(html: str):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, "html.parser")


def _texty(el) -> bool:
    """A text element she can type into: it has words of its own and no block-level children."""
    if el.name not in TEXT_TAGS:
        return False
    if el.name == "span" and not (el.get("class") or el.string):
        return False
    if el.find(["div", "section", "article", "ul", "ol", "form", "table", "p", "h1", "h2", "h3", "h4", "li"]):
        return False
    return bool(el.get_text(strip=True))


def tag(html: str) -> tuple[str, int]:
    """Number every editable element of one section that has no number yet. Returns (html, how many were added)."""
    soup = _soup(html)
    used = [int(x["data-e"]) for x in soup.find_all(attrs={"data-e": True}) if str(x["data-e"]).isdigit()]
    n = max(used, default=0)
    added = 0
    for el in soup.find_all(True):
        if el.has_attr("data-e"):
            continue
        if (el.name == "img" and el.has_attr("data-hoola-img")) or _texty(el):
            n += 1
            el["data-e"] = str(n)
            added += 1
    return (str(soup), added) if added else (html, 0)


def strip(html: str) -> str:
    """The published site never carries the edit numbers."""
    return EDIT_ATTR.sub("", html)


def _find(soup, e: str):
    el = soup.find(attrs={"data-e": str(e)})
    if el is None:
        raise EditError("Yeh hissa ab nahi mila (shayad section dobara bana). Preview taaza karke phir dabaiye.")
    return el


def _set_text(el, value: str) -> None:
    """New words for the element; an icon or picture inside it (a button's phone icon) stays where it was."""
    keep = [c for c in el.find_all(KEEP_INSIDE, recursive=False)]
    lead = bool(keep) and el.contents and el.contents[0] in keep
    el.clear()
    if keep and lead:
        for k in keep:
            el.append(k)
        el.append(" " + value)
    else:
        el.append(value)
        for k in keep:
            el.append(k)


def describe(html: str, e: str) -> dict[str, Any]:
    soup = _soup(html)
    el = _find(soup, e)
    kind = "image" if el.name == "img" else ("link" if el.name == "a" else "text")
    return {"e": str(e), "tag": el.name, "kind": kind, "text": el.get_text(" ", strip=True)[:MAX_TEXT],
            "href": el.get("href", "") if el.name == "a" else "", "img": el.get("data-hoola-img", "")}


def apply(html: str, e: str, op: str, value: str, photos: set[str], ok_href) -> tuple[str, str]:
    """One change to one element. Returns (new html, a short line for the history). Raises EditError in plain words."""
    soup = _soup(html)
    el = _find(soup, e)
    value = (value or "").strip()
    if op == "text":
        if el.name == "img":
            raise EditError("Yeh tasveer hai; tasveer badalne ke liye use chuniye.")
        if not value:
            raise EditError("Khaali nahi chhod sakte; hatana ho to 'Hatao' dabaiye.")
        value = re.sub(r"\s+", " ", value)[:MAX_TEXT]
        old = el.get_text(" ", strip=True)
        _set_text(el, value)
        what = f'"{old[:40]}" -> "{value[:40]}"'
    elif op == "link":
        if el.name != "a":
            raise EditError("Link sirf button / link par lagta hai.")
        if not ok_href(value):
            raise EditError("Yeh link nahi chalega: https://..., tel:, mailto: ya site ka apna page chahiye.")
        el["href"] = value
        if value.lower().startswith("https://"):
            el["rel"], el["target"] = "noopener", "_blank"
        else:
            el.attrs.pop("target", None)
        what = f"link -> {value[:60]}"
    elif op == "image":
        if el.name != "img":
            raise EditError("Yahan tasveer nahi hai.")
        if value not in photos:
            raise EditError("Yeh photo is website mein nahi hai; pehle photo jodiye.")
        el["data-hoola-img"] = value
        what = f"photo -> {value}"
    elif op == "remove":
        if el.name == "h1":
            raise EditError("Page ka mukhya heading (h1) hata nahi sakte; uske shabd badal dijiye.")
        what = f'hataya: "{el.get_text(" ", strip=True)[:40] or el.name}"'
        el.decompose()
    else:
        raise EditError("Yeh badlav samajh nahi aaya.")
    return str(soup), what

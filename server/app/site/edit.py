"""v0.295 Website editing like Lovable (web design Phase 2): she clicks a thing in the preview and changes it herself -
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
        if ((el.name == "img" and el.has_attr("data-hoola-img")) or _texty(el)
                or el.has_attr("data-hoola-media") or (el.name == "div" and el.has_attr("data-hoola-video"))):   # v0.338
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
        raise EditError("This part was not found (the section may have been rebuilt). Refresh the preview and tap again.")
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


BLOCKY = ("p", "h1", "h2", "h3", "h4", "h5", "h6", "figure", "ul", "ol", "table", "blockquote", "details", "form",
          "article", "div", "dl", "picture", "video", "audio")


def insert(html: str, e: str, markup: str) -> tuple[str, str]:
    """v0.338 something she adds (photo / video / audio / file) goes in right AFTER the block she clicked: a link, a
    word or a list item climbs to its paragraph / list / card first, so nothing lands inside a button or a heading."""
    soup = _soup(html)
    el = _find(soup, e)
    anchor = el
    while anchor.parent is not None and anchor.parent.name not in ("section", "[document]") and (
            anchor.name not in BLOCKY or anchor.find_parent(["a", "button", "li", "h1", "h2", "h3", "p"]) is not None):
        anchor = anchor.parent
    if anchor.name == "section":
        raise EditError("Nothing can be added here; click on something inside a section.")
    new = _soup(markup)
    for node in list(new.contents)[::-1]:
        anchor.insert_after(node)
    return str(soup), "jodi"


def describe(html: str, e: str) -> dict[str, Any]:
    soup = _soup(html)
    el = _find(soup, e)
    kind = ("image" if el.name == "img" else "media" if (el.has_attr("data-hoola-media") or el.has_attr("data-hoola-video"))
            else "link" if el.name == "a" else "text")
    return {"e": str(e), "tag": el.name, "kind": kind, "text": el.get_text(" ", strip=True)[:MAX_TEXT],
            "href": el.get("href", "") if el.name == "a" else "", "img": el.get("data-hoola-img", "")}


def apply(html: str, e: str, op: str, value: str, photos: set[str], ok_href) -> tuple[str, str]:
    """One change to one element. Returns (new html, a short line for the history). Raises EditError in plain words."""
    soup = _soup(html)
    el = _find(soup, e)
    value = (value or "").strip()
    if op == "text":
        if el.name == "img":
            raise EditError("This is a picture; select it to change the picture.")
        if not value:
            raise EditError("It cannot be left empty; tap 'Remove' to remove it.")
        value = re.sub(r"\s+", " ", value)[:MAX_TEXT]
        old = el.get_text(" ", strip=True)
        _set_text(el, value)
        what = f'"{old[:40]}" -> "{value[:40]}"'
    elif op == "link":
        if el.name != "a":
            raise EditError("A link can be set only on a button / link.")
        if not ok_href(value):
            raise EditError("This link will not work: it needs https://..., tel:, mailto: or one of the site's own pages.")
        el["href"] = value
        if value.lower().startswith("https://"):
            el["rel"], el["target"] = "noopener", "_blank"
        else:
            el.attrs.pop("target", None)
        what = f"link -> {value[:60]}"
    elif op == "image":
        if el.name != "img":
            raise EditError("There is no picture here.")
        if value not in photos:
            raise EditError("This photo is not in this website; add the photo first.")
        el["data-hoola-img"] = value
        what = f"photo -> {value}"
    elif op == "remove":
        if el.name == "h1":
            raise EditError("The page's main heading (h1) cannot be removed; change its words instead.")
        what = f'removed: "{el.get_text(" ", strip=True)[:40] or el.get("data-hoola-media") or el.name}"'
        box = el.find_parent(class_=["hs-emedia", "hs-efile"])     # v0.338 the photo / video / file she added goes as
        whole = box is not None and el.name != "figcaption"          # one piece; its caption alone when she picks that
        (box if whole else el).decompose()
    else:
        raise EditError("This change was not understood.")
    return str(soup), what


# ---------------------------------------------------------------- v0.795 YEH WALA: the free style panel
# Her style picks are utility classes (`hs-u-<prop>-<value>`, hoola-site.css) on the element - the site's OWN colour
# tokens, a type scale step, a spacing step, a corner, an alignment, a weight. No raw colour can be written: a value
# outside these lists is refused (the design-system rule), and no model is asked.
STYLE: dict[str, dict[str, str]] = {
    "color": {"primary": "the brand colour", "accent": "the accent", "ink": "the text colour", "muted": "soft text",
              "bg": "the page colour"},
    "bg": {"none": "no background", "primary": "the brand colour", "accent": "the accent", "surface": "a soft panel",
           "ink": "dark"},
    "size": {"m1": "smaller", "1": "a step bigger", "2": "two steps bigger", "3": "three steps bigger"},
    "space": {"0": "no padding", "1": "a little padding", "2": "some padding", "3": "more padding", "4": "lots of padding"},
    "radius": {"0": "square corners", "sm": "slightly round", "md": "round", "lg": "very round", "full": "pill"},
    "align": {"left": "left", "center": "centre", "right": "right"},
    "weight": {"400": "regular", "600": "semi-bold", "700": "bold"},
}
STYLE_LABEL = {"color": "text colour", "bg": "background", "size": "size", "space": "padding", "radius": "corners",
               "align": "alignment", "weight": "weight"}


def style(html: str, e: str, prop: str, value: str) -> tuple[str, str]:
    """One style pick for one element: replaces that property's old utility class ('default' removes it)."""
    prop, value = str(prop or "").strip(), str(value or "").strip()
    if prop not in STYLE:
        raise EditError("That style cannot be changed here.")
    if value != "default" and value not in STYLE[prop]:
        raise EditError("Only your website's own colours can be used." if prop in ("color", "bg")
                        else "That step is not on the list.")
    soup = _soup(html)
    el = _find(soup, e)
    cls = [c for c in (el.get("class") or []) if not c.startswith(f"hs-u-{prop}-")]
    if value != "default":
        cls.append(f"hs-u-{prop}-{value}")
    if cls:
        el["class"] = cls
    elif el.has_attr("class"):
        del el["class"]
    return str(soup), f"{STYLE_LABEL[prop]}: {'as designed' if value == 'default' else STYLE[prop][value]}"


def styles_of(html: str, e: str) -> dict[str, str]:
    """The style picks already on an element (for the panel)."""
    el = _find(_soup(html), e)
    out = {}
    for c in el.get("class") or []:
        m = re.match(r"hs-u-([a-z]+)-(.+)$", c)
        if m and m.group(1) in STYLE:
            out[m.group(1)] = m.group(2)
    return out

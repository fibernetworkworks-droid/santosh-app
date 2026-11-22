"""v0.999.119 D9 of docs/WEB_DESIGN_ENGINE_PLAN.md: "Upgrade this site" - her HTML website moved to the new engine.

Her tap starts it. Hoola rewrites the SAME website (same id, so the same forms, booking, shop, orders, blog, members,
photos and address) as a React website from the kit: its pages and sections from its plan (or the prototype she
approved), HER words read back out of the pages she has now (her edits included, never rewritten by a model), her
colour pinned in the new design. It is built BESIDE the old website: nothing she has changes while it is made, her
preview and her live address keep the old design. She looks at both side by side, then:
- Keep the new design (her tap, on the fingerprint of the version she saw) -> the website is the React one from now
  on; her address changes only when she puts it live with the normal launch card (her tap again).
- Go back to the old design (any time) -> the HTML website again, untouched all along; the new one is kept to look at.
- Throw it away -> the new one is removed; the old website is as it was.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from html.parser import HTMLParser
from typing import Any

from ..db import now

log = logging.getLogger("santosh.site")
KEY = "react_upgrade"                                 # facts key while the new design waits for her (beside the old)
KEPT = "html_kept"                                    # facts key after she kept it: the old design to go back to
_LOCK = threading.Lock()


class UpgradeError(Exception):
    def __init__(self, msg: str, code: int = 400):
        super().__init__(msg)
        self.code = code


def _j(s: Any, d: Any) -> Any:
    if isinstance(s, (dict, list)):
        return s
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def _t(x: Any, n: int) -> str:
    return " ".join(str(x or "").split())[:n]


def on() -> bool:
    from ..config import get_settings
    st = get_settings()
    return bool(getattr(st, "site_upgrade", True)) and bool(getattr(st, "app_engine", True))


# ---------------------------------------------------------------- 1. her words, read back out of her pages
class _Node:
    __slots__ = ("tag", "cls", "kids", "_in_card")

    def __init__(self, tag: str, cls: str):
        self.tag, self.cls, self.kids, self._in_card = tag, cls, [], False


class _Tree(HTMLParser):
    """A light tree of one built section (text nodes are plain strings)."""
    VOID = {"br", "img", "hr", "input", "meta", "link", "source", "wbr", "area", "col", "embed", "track"}
    SKIP = {"script", "style", "svg", "noscript", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("root", "")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        n = _Node(tag, dict(attrs).get("class") or "")
        self.stack[-1].kids.append(n)
        if tag not in self.VOID:
            self.stack.append(n)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].kids.append(data)


def _skip(n: _Node) -> bool:
    c = n.cls.split()
    return n.tag in _Tree.SKIP or "blank" in c or "sr" in c or "sr-only" in c


def _text(n) -> str:
    if isinstance(n, str):
        return n
    if _skip(n):
        return ""
    return (" " if n.tag == "br" else "").join(_text(k) for k in n.kids)


def _walk(n: _Node):
    for k in n.kids:
        if isinstance(k, _Node) and not _skip(k):
            yield k
            yield from _walk(k)


CARDS = {"article", "li", "details", "figure", "blockquote", "tr"}
HEADS = ("h3", "h4", "h5", "summary", "dt", "th", "strong", "b")
LINES = ("p", "dd", "td", "figcaption", "span", "blockquote", "em")


def _is_card(n: _Node) -> bool:
    return n.tag in CARDS or "card" in n.cls.split()


def words_of(html: str) -> dict[str, Any]:
    """{heading, line, items, cta} of one built section, as her website shows it now; blanks she never filled are left
    out (they are not her words)."""
    t = _Tree()
    try:
        t.feed(html or "")
        t.close()
    except Exception:                                 # noqa: BLE001 - a section that does not read gives no words
        return {}
    out: dict[str, Any] = {}
    items: list[str] = []
    for n in _walk(t.root):
        inside = n._in_card
        if _is_card(n) and not inside:
            for d in _walk(n):
                d._in_card = True
            heads = [_t(_text(d), 120) for d in _walk(n) if d.tag in HEADS and _t(_text(d), 120)]
            lines = [_t(_text(d), 120) for d in _walk(n) if d.tag in LINES and _t(_text(d), 120)]
            lines = [x for x in lines if x not in heads and not any(x in h for h in heads)]
            it = (heads[0] + (" - " + lines[0] if lines else "")) if heads else (lines[0] if lines else _t(_text(n), 120))
            it = _t(it, 120)
            if it and it not in items:
                items.append(it)
            continue
        if inside:
            continue
        txt = _t(_text(n), 320)
        if not txt:
            continue
        if n.tag in ("h1", "h2") and "heading" not in out:
            out["heading"] = _t(txt, 90)
        elif n.tag in ("a", "button") and "btn" in n.cls and "cta" not in out:
            out["cta"] = _t(txt, 40)
        elif n.tag == "p" and "line" not in out and "eyebrow" not in n.cls.split():
            out["line"] = txt
        elif n.tag == "li" and len(items) < 8:
            items.append(_t(txt, 120))
    if items:
        out["items"] = items[:8]
    return out


def pages_from_site(r) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Her website as prototype-shaped pages for the writer: the pages + sections of the prototype she approved (else
    of its plan), each section with the words her website shows now. Returns (pages, counts)."""
    from . import prototype as PT
    from . import service as S
    m = PT.meta(r)
    pages = PT.pages_of(r, m.get("approved_v")) if m.get("approved_v") else []
    if not pages:
        pages = PT.skeleton(_j(r.plan, {}))
    built = S._sections(r)
    n_sec = n_words = 0
    out = []
    for pg in pages:
        secs = []
        for sec in pg.get("sections") or []:
            n_sec += 1
            got = words_of(str((built.get(f"{pg['slug']}__{sec.get('type')}") or {}).get("html") or ""))
            if got:
                n_words += 1
                sec = {**{k: v for k, v in sec.items() if k not in ("draft",)}, **got}
                if "items" not in got and sec.get("items"):
                    sec["items"] = sec["items"]
            secs.append(sec)
        out.append({**pg, "sections": secs})
    return out, {"pages": len(out), "sections": n_sec, "with_her_words": n_words}


# ---------------------------------------------------------------- 2. the state of an upgrade
def site_of(tenant: str, ref: str):
    """Her website (her own only; another person's site is not found)."""
    from ..db import session
    from . import service as S
    with session() as s:
        r = S._find(s, tenant, ref)
        s.expunge(r)
    return r


def state(r) -> dict[str, Any]:
    return dict(_j(r.facts, {}).get(KEY) or {})


def kept(r) -> dict[str, Any]:
    return dict(_j(r.facts, {}).get(KEPT) or {})


def _set(site_id: str, **fields) -> dict[str, Any]:
    """Change the upgrade's record (and only it) in the site's facts, under the lock."""
    from . import service as S
    with _LOCK:
        r = S._load(site_id)
        facts = _j(r.facts, {})
        cur = dict(facts.get(KEY) or {})
        for k, v in fields.items():
            if v is None:
                cur.pop(k, None)
            else:
                cur[k] = v
        facts[KEY] = cur
        S._save(site_id, facts=json.dumps(facts))
        return cur


def fingerprint(link: dict[str, Any]) -> str:
    """What she looked at: the new app's built version."""
    base = f"{link.get('id')}|{link.get('version')}|{link.get('preview')}"
    return hashlib.sha256(base.encode()).hexdigest()[:16]


def why_not(r) -> str:
    """The reason Upgrade cannot start on this website, or "" when it can."""
    from . import prototype as PT
    if not on():
        return "Upgrading websites is switched off on this server."
    if getattr(r, "draft_of", ""):
        return "This is a draft; upgrade the website itself, not its draft."
    if PT.react_link(r).get("id"):
        return "This website is already on the new design engine."
    if not r.version:
        return "The website is not built yet; build it first, then upgrade it."
    if state(r).get("status") == "building":
        return "The new design is already being made."
    if state(r).get("status") == "ready":
        return "A new design is already waiting; compare it, then keep it or throw it away."
    if r.status in ("building", "planning", "making", "looks"):
        return "The website is being changed right now; upgrade it when that is done."
    return ""


def view(r) -> dict[str, Any]:
    from . import service as S
    st = state(r)
    out: dict[str, Any] = {"can": not why_not(r), "why_not": why_not(r), "before": S.preview_url(r, short=True)}
    if st:
        out.update({k: st.get(k) for k in ("status", "started_at", "done_at", "error", "counts", "blanks", "fixed",
                                           "written", "critic")})
        if st.get("status") == "ready":
            out["after"] = st.get("preview") or ""
            out["hash"] = fingerprint(st)
    k = kept(r)
    if k:
        out["kept"] = {"version": k.get("version"), "at": k.get("at"), "can_go_back": True}
    return out


# ---------------------------------------------------------------- 3. her taps
def start(tenant: str, ref: str) -> dict[str, Any]:
    """HER TAP (the Studio route): make the new design of this website beside the old one."""
    from . import service as S
    r = site_of(tenant, ref)
    why = why_not(r)
    if why:
        raise UpgradeError(why, 409)
    _set(r.id, status="building", started_at=now().isoformat(), error="", done_at=None)
    _spawn(job, r.id)
    S._emit(S._load(r.id))
    return {**view(S._load(r.id)), "say": "Making the new design of your website. Your website stays as it is meanwhile."}


def _spawn(fn, site_id: str) -> None:
    threading.Thread(target=fn, args=(site_id,), daemon=True, name=f"upgrade-{site_id}").start()


def job(site_id: str) -> None:
    """The new design, built beside the old website: nothing of the old one is changed here."""
    from ..usage import scope
    from . import prototype as PT
    from . import service as S
    r = S._load(site_id)
    with scope(r.tenant_id, "site"):
        try:
            pages, counts = pages_from_site(r)
            if not pages:
                raise UpgradeError("The website has no pages to move.")
            facts = _j(r.facts, {})
            wfacts = {**{k: v for k, v in facts.items() if k not in (KEY, KEPT, "react_app")}, "_site": PT.site_link(r)}
            pin = str((_j(r.look, {}).get("tokens") or {}).get("primary") or "")   # the colour of her website now
            step = lambda a, b, c="": S._work(S._load(site_id), a, b, c)   # noqa: E731
            link, res, st, review = PT.write_react(
                r, pages, wfacts, state(r).get("id") or "", step=step, pin=pin,
                start=f"{counts['pages']} pages of your website, with your words, in the new design")
            ok = bool(res.get("built"))
            _set(site_id, **link, status="ready" if ok else "failed", counts=counts, done_at=now().isoformat(),
                 error="" if ok else _t("The new design did not build: " + str(res.get("say") or ""), 300))
            S._work(S._load(site_id), "done" if ok else "error",
                    "The new design is ready - compare it with your website" if ok else "The new design hit a problem",
                    (f"{counts['with_her_words']} of {counts['sections']} sections with your own words"
                     + (f"; fill in: {', '.join(st['blanks'])}" if st.get("blanks") else "")) if ok else str(res.get("say") or "")[:200])
        except Exception as e:                        # noqa: BLE001 - the old website is untouched either way
            log.exception("website upgrade failed")
            _set(site_id, status="failed", error=_t(f"The new design could not be made: {e}", 300), done_at=now().isoformat())
        S._emit(S._load(site_id), push=True)


def accept(tenant: str, ref: str, h: str) -> dict[str, Any]:
    """HER TAP: keep the new design. The website is the React one from now on; her live address changes only when she
    puts it live with the launch card."""
    from . import service as S
    r = site_of(tenant, ref)
    st = state(r)
    if st.get("status") != "ready" or not st.get("id"):
        raise UpgradeError("There is no new design ready to keep.", 409)
    if not h or h != fingerprint(st):
        raise UpgradeError("The new design changed after you looked; look at it again, then keep it.", 409)
    with _LOCK:
        r = S._load(r.id)
        facts = _j(r.facts, {})
        link = {k: v for k, v in (facts.get(KEY) or {}).items() if k not in ("status", "started_at", "done_at", "error")}
        facts["react_app"] = {**link, "upgraded": True}
        facts[KEPT] = {"version": r.version, "at": now().isoformat()}
        facts.pop(KEY, None)
        S._save(r.id, facts=json.dumps(facts))
    r = S._load(r.id)
    S._emit(r)
    from . import hosting as H
    live = bool(H.live_version(r))
    return {**S.view(r), "upgrade": view(r),
            "say": "Your website now uses the new design." + (
                " Your live address still shows the old one until you put the website live again." if live else "")}


def back(tenant: str, ref: str) -> dict[str, Any]:
    """HER TAP: go back to the old design (the HTML website, never changed). The new one waits beside it again."""
    from . import service as S
    r = site_of(tenant, ref)
    if not kept(r):
        raise UpgradeError("This website has no old design kept to go back to.", 409)
    with _LOCK:
        r = S._load(r.id)
        facts = _j(r.facts, {})
        link = {k: v for k, v in (facts.get("react_app") or {}).items() if k != "upgraded"}
        facts.pop("react_app", None)
        facts.pop(KEPT, None)
        if link.get("id"):
            facts[KEY] = {**link, "status": "ready", "done_at": now().isoformat()}
        S._save(r.id, facts=json.dumps(facts))
    r = S._load(r.id)
    S._emit(r)
    from . import hosting as H
    live = bool(H.live_version(r))
    return {**S.view(r), "upgrade": view(r),
            "say": "Your website is back on its old design." + (
                " If the new design is live on your address, put the website live again to show the old one." if live else "")}


def discard(tenant: str, ref: str) -> dict[str, Any]:
    """HER TAP: throw the new design away (only while it waits beside the old website)."""
    from ..appengine import service as AE
    from . import service as S
    r = site_of(tenant, ref)
    st = state(r)
    if not st:
        raise UpgradeError("There is no new design to throw away.", 404)
    if st.get("status") == "building":
        raise UpgradeError("The new design is still being made; throw it away when it is done.", 409)
    if st.get("id"):
        try:
            AE.delete_app(r.tenant_id, st["id"])
        except Exception:                             # noqa: BLE001 - already gone: only the record is left
            log.info("upgrade app not removed", exc_info=True)
    with _LOCK:
        r = S._load(r.id)
        facts = _j(r.facts, {})
        facts.pop(KEY, None)
        S._save(r.id, facts=json.dumps(facts))
    r = S._load(r.id)
    S._emit(r)
    return {**S.view(r), "upgrade": view(r), "say": "The new design is thrown away; your website is as it was."}


def summary(r) -> str:
    """One line for the chat about this website's upgrade (nothing is started from the chat)."""
    v = view(r)
    if v.get("kept"):
        return "This website was upgraded to the new design; the old design is kept to go back to."
    s = v.get("status")
    if s == "building":
        return "The new design of this website is being made beside it."
    if s == "ready":
        return "The new design is ready: compare it with the website in the Studio, then keep it or not."
    if s == "failed":
        return "The new design did not work out: " + str(v.get("error") or "")
    return ("This website can be upgraded to the new design (her tap in the Studio)." if v["can"]
            else re.sub(r"\s+", " ", v["why_not"]))

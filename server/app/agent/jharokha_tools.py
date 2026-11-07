"""v0.665.0 JHAROKHA MANCH - the T3 local-browser family, backend-only (built as 0.664.0 - their ASLI SAMAY took 0.664.0 while JHAROKHA sat built - REBASE PROTOCOL #12, both kept; owner: "T3 Local Browser ---
CONTINUE" - the T3 tier of download/HOOLA_MCP_FEED.json, the zero-login / zero-key browser rows).

A jharokha (झरोखा) is the overhanging window of an old haveli: you open it, look out at the street,
point at things, and the street does not come inside. That is this lane: the agent's OWN headless
Chromium, driven deterministically, one action per call - the page's structure comes back as a
readable tree with refs, and every click/type lands through a ref the agent just saw.

The T3 catalog rows this lane ports (both MIT, both zero-login / zero-key, both
catalog-description-verified; IDEA-ONLY - zero upstream code, zero new pip, zero new keys; the
browser is the house's OWN playwright>=1.48 + chromium, already installed for Motion v0.63 and the
Computer Operator v0.67):

- microsoft/playwright-mcp: "A Model Context Protocol (MCP) server that provides browser automation
  capabilities using Playwright. This server enables LLMs to interact with web pages through
  structured accessibility snapshots, bypassing the need for screenshots or visually-tuned models."
  -> the whole lane shape: snapshot-with-refs over pixels, a fresh snapshot after every action,
  refs valid until the page changes, one deterministic action per call.
- modelcontextprotocol/servers - Puppeteer (archived reference): "Browser automation and web
  scraping." -> the headless-browser doors themselves: navigate, click, fill, keyboard, screenshot,
  several tabs.

THE LANES (ONE tool `jharokha`, nine actions; every answer one envelope):

- `open` {url} - navigate the current tab (or open the first one): SSRF-guarded public http(s) only,
  plus the lane's own inert local schemes (about:blank, data:text/html capped) the tests and the
  agent's own scratch pages ride; returns {page, tree, text} - the snapshot rides every answer.
- `snapshot` {} - the current tab's interactive tree with refs (ref=eN) + the page's visible text.
  The playwright-mcp law: refs live until the page changes; a stale ref is an honest NOT_FOUND that
  says "take a fresh snapshot". No page open yet = NOT_FOUND too - this lane never invents a page.
- `click` {ref} - ONE real click through the ref (get_by_role(role, name).nth(n), the tag verified
  before the click so a stale ref cannot land on a stranger), then wait + a fresh snapshot.
- `type` {ref, text, submit?} - fill a textbox / searchbox / contenteditable (a combobox takes
  select_option), optionally pressing Enter after; then a fresh snapshot.
- `press` {key} - ONE key on the focused element; the allowlist is named (Enter, Tab, Escape,
  Backspace, Delete, arrows, Home/End/PageUp/PageDown/Space, one character) - no chords, no scripts.
- `console` {clear?} - this browser's own console tail: page log lines + uncaught page errors,
  newest last, capped; clear=true empties it. The page talks; the lane repeats.
- `tabs` {op: list | select | new | close, index?} - this tenant's tabs, capped (RAM law); `new`
  takes an optional url (same guard); closing the last tab closes the browser.
- `screenshot` {full?} - ONE PNG of the current tab into this tenant's own dir
  (data/jharokha/<tenant>/shot-*.png), path + bytes back, never base64; a too-big page is an honest
  TOO_BIG, not a cropped lie.
- `close` {} - close this tenant's browser NOW (RAM hygiene); the next open relaunches clean.

THE LAWS:

- RAM discipline (MEM-CURE): at most _MAX_BROWSERS tenant browsers alive at once (an extra tenant is
  an honest BUSY), at most _MAX_TABS tabs per tenant, and an idle reaper closes any browser idle
  longer than _IDLE_S - reaped on the reaper's tick and again defensively before every action. One
  owner loop owns all of playwright forever (its objects are loop-bound); actions are submitted
  thread-safe onto it, serialized per tenant with one lock, each with a hard belt timeout.
- SSRF guard: http/https go through the house's own scrape-lane guard (public IPs only - loopback,
  RFC1918, link-local and the cloud-metadata address never fetched); about:blank and data:text/html
  are allowed as inert local pages (no host, no network), everything else refused.
- Ephemeral by design: no profile, no cookies on disk, nothing shared across tenants - each launch
  starts clean, an honest window and not a second identity.
- Read-safe outputs: the tree lines, the page text and the console messages pass operator.browser
  mask_ids like every other scraping surface; navigation truth (page.url, the tab title) and local
  file paths do not - masked hrefs would be unreadable, and the model clicks by ref, never by a
  retyped URL.
- No evaluate, no downloads, no file://, no uploads, no credentials: the deterministic surface is
  open / look / click / type / press / read-the-console / tabs / one picture / close. Anything
  beyond that is the Computer Operator's agentic door (browser_worker), not this lane.

Envelope (the v0.559 discipline shape, same as reach / speckit / sandarbh / bhandar):
{schema_version, ok, tool, action, ..., meta{elapsed_ms, ...}, error{code, message, hint}} - the
model branches on ok / error.code, never on prose. Kill switch `jharokha_enabled` stops the whole
lane with the honest NEED_SETUP. Off means off.
"""
from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import get_settings
from .scrape_tools import ToolError  # the house's own tool error (the guard raises it)
from .tools import Ctx

log = logging.getLogger("santosh.jharokha")

SCHEMA_VERSION = 1

# ---------------------------------------------------------------- error codes (the discipline)
NEED_SETUP = "NEED_SETUP"      # the lane is off, or the browser stack itself is missing
BAD_INPUT = "BAD_INPUT"        # the arguments were rejected (the message names what and why)
NOT_FOUND = "NOT_FOUND"        # no page open / unknown tab / a stale or unknown ref
TOO_BIG = "TOO_BIG"            # a cap would be blown (tabs, data-url, screenshot bytes)
BLOCKED = "BLOCKED"            # the SSRF / scheme guard refused this url
BROWSER_ERROR = "BROWSER_ERROR"  # the browser itself failed (crash, navigation timeout, gone)
BUSY = "BUSY"                  # the global browser cap is held by other tenants right now

# ---------------------------------------------------------------- caps (generous, but the envelope stays small)
_MAX_NODES = 250               # interactive elements per snapshot
_MAX_NAME = 80                 # accessible-name chars per element
_MAX_TREE_CHARS = 16_000       # the tree's text cap
_MAX_PAGE_TEXT = 4_000         # the visible-text cap per snapshot
_MAX_TABS = 4                  # tabs per tenant browser (RAM law)
_MAX_BROWSERS = 2              # tenant browsers alive across the whole server (RAM law)
_MAX_CON = 40                  # console rows kept per tenant
_MAX_CON_CHARS = 200           # console row text cap
_MAX_DATA_URL = 16_000         # a data: url IS the page - cap it
_MAX_TEXT_ARG = 4_000          # chars typed in one `type` call
_MAX_SHOT_BYTES = 5_000_000    # one PNG, then TOO_BIG
_MAX_URL = 2_048               # navigation url length
_IDLE_S = 180                  # a browser idle this long is closed by the reaper (RAM law)
_REAP_TICK_S = 30              # the reaper's tick
_ACTION_TIMEOUT_S = 60         # the belt around one action on the owner loop
_NAV_TIMEOUT_MS = 20_000       # one page.goto
_STEP_TIMEOUT_MS = 8_000       # one click / fill / press

_JH_ACTIONS = ("open", "snapshot", "click", "type", "press", "console", "tabs", "screenshot", "close")

_TENANT_DIR = "jharokha"       # data/jharokha/<safe-tenant>/ - this lane's own dir

# the keys `press` may send - named, no chords, no scripts
_PRESS_KEYS = {"Enter", "Tab", "Escape", "Backspace", "Delete", "ArrowUp", "ArrowDown",
               "ArrowLeft", "ArrowRight", "Home", "End", "PageUp", "PageDown", "Space"}
_PRESS_ONE = re.compile(r"^[a-zA-Z0-9]$")
# roles get_by_role accepts AND this lane hands out refs for (interactive + the reading anchors)
_ROLE_OK = {"button", "link", "checkbox", "radio", "textbox", "searchbox", "combobox", "listbox",
            "option", "menuitem", "menuitemcheckbox", "menuitemradio", "tab", "switch", "slider",
            "treeitem", "spinbutton", "heading"}
_FILL_ROLES = {"textbox", "searchbox", "spinbutton", "combobox", "listbox"}

# the walk: every interactive element the page really shows, in DOM order, with the honest name.
# House-sized playwright-mcp idea: the a11y snapshot's role+name shape, rebuilt on the DOM because
# playwright 1.57 has no page.accessibility - and a walk we can re-run is exactly what makes a ref
# resolvable (role + name + nth among the same) and verifiable (the tag must still match).
_WALK_JS = """
() => {
  const MAXN = %d;
  const ACT = new Set(%s);
  const TAGROLE = {a: "link", button: "button", select: "combobox", textarea: "textbox",
                   summary: "button", option: "option", h1: "heading", h2: "heading", h3: "heading"};
  const TYPEMAP = {text: "textbox", search: "searchbox", email: "textbox", password: "textbox",
                   tel: "textbox", url: "textbox", number: "spinbutton", checkbox: "checkbox",
                   radio: "radio", range: "slider", submit: "button", button: "button",
                   reset: "button", file: "button", date: "textbox", time: "textbox"};
  function roleName(el) {
    const r = (el.getAttribute("role") || "").trim().toLowerCase();
    if (r && ACT.has(r)) return r;
    const t = el.tagName.toLowerCase();
    if (t === "input") return TYPEMAP[(el.getAttribute("type") || "text").toLowerCase()] || "textbox";
    if (t === "select" && el.multiple) return "listbox";
    return TAGROLE[t] || "";
  }
  function vis(el) {
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden") return false;
    const r = el.getBoundingClientRect();
    return (r.width > 1 && r.height > 1) || el.tagName === "OPTION";
  }
  function nameOf(el) {
    const t = el.tagName.toLowerCase();
    let n = el.getAttribute("aria-label") || "";
    if (!n) {
      try { if (el.labels && el.labels.length) n = el.labels[0].innerText || ""; } catch (e) {}
    }
    if (!n && (t === "input" || t === "textarea")) n = el.getAttribute("placeholder") || "";
    if (!n && t === "img") n = el.getAttribute("alt") || "";
    if (!n) n = (el.innerText || el.value || "").trim();
    return n.replace(/\\s+/g, " ").slice(0, %d);
  }
  function depthOf(el) { let d = 0, n = el; while (n && n !== document.body) { n = n.parentElement; d++; } return d; }
  const els = [...document.querySelectorAll(
    "a[href], button, input, select, textarea, summary, h1, h2, h3, [role], [onclick], [contenteditable='true']")];
  const out = [];
  const seen = new Set();
  for (const el of els) {
    if (out.length >= MAXN) break;
    if (!el || seen.has(el)) continue;
    seen.add(el);
    if (el.closest("[aria-hidden='true']")) continue;
    if (!vis(el)) continue;
    const role = roleName(el);
    if (!role) continue;
    const tag = el.tagName.toLowerCase();
    const locked = tag === "input" || tag === "textarea" || tag === "select"
        ? (el.disabled || el.readOnly) : false;
    out.push({
      role, tag,
      name: nameOf(el),
      href: tag === "a" ? (el.href || "") : "",
      value: (tag === "input" || tag === "textarea") ? String(el.value ?? "").slice(0, 60) : "",
      level: /^h[1-6]$/.test(tag) ? Number(tag[1]) : 0,
      disabled: locked,
      editable: tag === "textarea" || el.getAttribute("contenteditable") === "true" ||
                (tag === "input" && !locked &&
                 ["textbox", "searchbox", "spinbutton"].includes(role)),
      depth: Math.min(depthOf(el), 12),
    });
  }
  return out;
}
""" % (_MAX_NODES, ", ".join(f'"{r}"' for r in sorted(_ROLE_OK - {"heading"})), _MAX_NAME)

_TAG_JS = "el => el.tagName.toLowerCase()"


def _clean(value: Any, cap: int) -> str:
    return " ".join(str(value or "").split())[:cap]


def _mask_text(v: str) -> str:
    """ID numbers in what comes back are masked before the chat model reads it (the scrape-lane law)."""
    try:
        from ..operator.browser import mask_ids
        return mask_ids(v)
    except Exception:                                   # pragma: no cover - the operator lane is missing
        return v


# ---------------------------------------------------------------- envelope (the discipline)

def _jh_envelope(action: str, error: tuple[str, str, str] | None = None, elapsed_ms: int = 0,
                 **fields) -> dict:
    out: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "ok": error is None, "tool": "jharokha",
                           "action": action,
                           "error": (None if error is None else
                                     {"code": error[0], "message": error[1], "hint": error[2]})}
    out.update(fields)
    meta = dict(out.pop("meta", {}) or {})
    out["meta"] = {"elapsed_ms": max(0, int(elapsed_ms)),
                   "browser": "chromium (headless, local - zero login, zero key)", **meta}
    return out


def _jh_bad(action: str, msg: str, hint: str = "", code: str = BAD_INPUT) -> dict:
    return _jh_envelope(action, error=(code, msg, hint))


def _locked(action: str) -> dict | None:
    if not bool(getattr(get_settings(), "jharokha_enabled", True)):
        return _jh_envelope(action, error=(
            NEED_SETUP, "the jharokha local-browser lane is turned off on this server",
            "Ask the owner to set jharokha_enabled=true."))
    if _PW_MISSING:
        return _jh_envelope(action, error=(
            NEED_SETUP, f"the browser stack is not installed on this server ({_PW_MISSING})",
            "Ask the owner to run: python -m playwright install --with-deps chromium"))
    return None


# ---------------------------------------------------------------- the url guard (the SSRF law)

def _guard_url(url: str) -> str:
    """Public http(s) through the house's own scrape-lane guard; about:blank and data:text/html ride
    as inert local pages (no host, no network); everything else is refused by name."""
    raw = str(url or "").strip()
    if not raw:
        raise ToolError("Give the page a link (url)")
    if raw == "about:blank":
        return raw
    if raw.startswith("data:"):
        if not raw.lower().startswith("data:text/html"):
            raise ToolError("Only data:text/html pages ride the local lane (this one is another kind)")
        if len(raw) > _MAX_DATA_URL:
            raise ToolError(f"The data: page is longer than the {_MAX_DATA_URL}-char local cap")
        return raw
    if len(raw) > _MAX_URL:
        raise ToolError("That link is too long")
    from .scrape_tools import _guard_url as _house_guard
    return _house_guard(raw)   # ToolError on anything that is not a public http(s) host


# ---------------------------------------------------------------- the owner loop (playwright's one home)

_PW_MISSING = ""
try:
    from playwright.async_api import Page  # noqa: F401 - presence check only
except Exception as _e:                                 # pragma: no cover - the stack is missing
    _PW_MISSING = str(_e)[:120]

_OWNER: dict[str, Any] = {"loop": None, "thread": None, "pw": None, "cm": None, "reaper": None,
                          "stop": None, "ready": None, "err": None}
_TENANTS: dict[str, dict] = {}          # tenant -> browser state (map guarded by _TEN_LOCK)
_TEN_LOCK = threading.Lock()            # guards the tenant MAP, never a page action
_LOCKS: dict[str, asyncio.Lock] = {}    # per-tenant action locks - touched ONLY on the owner loop


def _owner_ready() -> bool:
    return _OWNER["pw"] is not None and _OWNER["loop"] is not None


def _ensure_owner() -> None:
    """Start the owner loop once: one daemon thread that owns playwright (its objects are loop-bound)
    forever, reaps idle browsers, and takes action coroutines thread-safely."""
    with _TEN_LOCK:
        if _owner_ready():
            return
        if _OWNER["thread"] is not None and _OWNER["thread"].is_alive():
            if _OWNER["ready"] is not None:
                _OWNER["ready"].wait(timeout=15)
            if _owner_ready():
                return
        _OWNER.update(loop=None, pw=None, cm=None, reaper=None, err=None)
        _OWNER["stop"] = threading.Event()
        _OWNER["ready"] = threading.Event()
        t = threading.Thread(target=lambda: asyncio.run(_run_owner()), name="jharokha-owner",
                             daemon=True)
        _OWNER["thread"] = t
        t.start()
        _OWNER["ready"].wait(timeout=30)
    if not _owner_ready():
        err = _OWNER.get("err")
        raise RuntimeError("the browser lane could not start" +
                           (f": {err}" if err else " (playwright did not come up)"))


async def _run_owner() -> None:
    """The owner loop's body: playwright enters here and NEVER leaves until shutdown."""
    loop = asyncio.get_running_loop()
    _OWNER["loop"] = loop
    try:
        from playwright.async_api import async_playwright
        cm = async_playwright()
        pw = await cm.__aenter__()
        _OWNER["pw"], _OWNER["cm"] = pw, cm
        _OWNER["reaper"] = loop.create_task(_reaper())
    except Exception as e:                              # pragma: no cover - browser stack broken
        _OWNER["err"] = e
        log.error("jharokha owner could not start playwright: %s", e)
    finally:
        _OWNER["ready"].set()
    if _OWNER["pw"] is None:
        return
    stop_ev = asyncio.Event()

    def _watch() -> None:
        _OWNER["stop"].wait()
        loop.call_soon_threadsafe(stop_ev.set)

    threading.Thread(target=_watch, name="jharokha-stop", daemon=True).start()
    await stop_ev.wait()


async def _reaper() -> None:
    """RAM discipline: a browser idle longer than _IDLE_S is closed wherever the tick finds it."""
    while True:
        await asyncio.sleep(_REAP_TICK_S)
        try:
            await _reap_once()
        except Exception:                               # pragma: no cover - the reaper never dies loudly
            log.exception("jharokha reaper tick failed")


async def _reap_once() -> int:
    now = time.monotonic()
    with _TEN_LOCK:
        stale = [t for t, st in _TENANTS.items() if now - st["used"] > _IDLE_S]
    for t in stale:
        try:
            await _close_tenant(t)
            log.info("jharokha reaped the idle browser of tenant %s", t[:24])
        except Exception:                               # pragma: no cover
            log.exception("jharokha could not reap tenant %s", t[:24])
    return len(stale)


async def _close_tenant(tenant: str) -> int:
    """Close one tenant's browser NOW and forget it; returns how many pages died."""
    with _TEN_LOCK:
        st = _TENANTS.pop(tenant, None)
    if st is None:
        return 0
    st["dropped"] = True
    n = len(st["pages"])
    for p in st["pages"]:
        try:
            await p.close()
        except Exception:
            pass
    try:
        if st.get("context"):
            await st["context"].close()
    except Exception:
        pass
    try:
        if st.get("browser"):
            await st["browser"].close()
    except Exception:
        pass
    return n


async def _aclose_all() -> int:
    """Every tenant browser closed (tests + shutdown)."""
    with _TEN_LOCK:
        tenants = list(_TENANTS.keys())
    n = 0
    for t in tenants:
        try:
            n += await _close_tenant(t)
        except Exception:                               # pragma: no cover
            pass
    return n


def _shutdown_owner(timeout: float = 20.0) -> None:
    """Tests / process exit: close every browser, stop the reaper, put playwright down, join."""
    loop = _OWNER.get("loop")

    async def _die() -> None:
        r = _OWNER.get("reaper")
        if r:
            r.cancel()
        await _aclose_all()
        cm = _OWNER.get("cm")
        if cm:
            try:
                await cm.__aexit__(None, None, None)
            except Exception:
                pass

    if loop is not None:
        try:
            fut = asyncio.run_coroutine_threadsafe(_die(), loop)
            fut.result(timeout=timeout)
        except Exception:                               # pragma: no cover
            pass
    stop = _OWNER.get("stop")
    if stop is not None:
        stop.set()
    t = _OWNER.get("thread")
    if t is not None and t.is_alive():
        t.join(timeout=5)
    _OWNER.update(loop=None, thread=None, pw=None, cm=None, reaper=None)


async def _owned(coro, timeout: float = _ACTION_TIMEOUT_S):
    """Run one action coroutine on the owner loop and await it here, with the hard belt."""
    _ensure_owner()
    loop = _OWNER["loop"]
    fut = asyncio.run_coroutine_threadsafe(coro, loop)
    try:
        return await asyncio.wait_for(asyncio.wrap_future(fut), timeout=timeout)
    except asyncio.TimeoutError:
        fut.cancel()
        raise


# ---------------------------------------------------------------- the tenant browser (launch + state)

async def _get_tenant(tenant: str) -> dict:
    """This tenant's browser, launched lazily; the global cap is the RAM law."""
    with _TEN_LOCK:
        st = _TENANTS.get(tenant)
        if st is not None and not st.get("dropped"):
            st["used"] = time.monotonic()
            return st
    pw = _OWNER["pw"]
    if pw is None:
        raise RuntimeError("the browser lane is not running")
    with _TEN_LOCK:
        alive = [t for t, s in _TENANTS.items() if not s.get("dropped")]
        if len(alive) >= _MAX_BROWSERS and tenant not in alive:
            raise _Busy()
    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
    context = await browser.new_context(viewport={"width": 1280, "height": 860})
    context.set_default_timeout(_STEP_TIMEOUT_MS)
    st = {"browser": browser, "context": context, "pages": [], "current": -1, "refs": {},
          "gen": 0, "con": deque(maxlen=_MAX_CON), "used": time.monotonic(),
          "dropped": False, "seq": 0}

    def _on_console(msg) -> None:
        st["con"].append({"type": _clean(msg.type, 12), "text": _clean(msg.text, _MAX_CON_CHARS),
                          "at": datetime.now().isoformat(timespec="seconds")})

    def _on_pageerror(err) -> None:
        st["con"].append({"type": "pageerror", "text": _clean(err, _MAX_CON_CHARS),
                          "at": datetime.now().isoformat(timespec="seconds")})

    def _on_close(page) -> None:
        try:
            st["pages"] = [p for p in st["pages"] if p is not page]
            if st["pages"]:
                st["current"] = min(max(0, st["current"]), len(st["pages"]) - 1)
            else:
                st["current"] = -1
            st["refs"], st["gen"] = {}, st["gen"] + 1
        except Exception:                               # pragma: no cover
            pass

    st["on_console"], st["on_pageerror"], st["on_close"] = _on_console, _on_pageerror, _on_close
    with _TEN_LOCK:
        old = _TENANTS.get(tenant)
        if old is not None and not old.get("dropped"):
            st = old                                    # another action won the launch race
            try:
                await context.close()
                await browser.close()
            except Exception:
                pass
            st["used"] = time.monotonic()
            return st
        _TENANTS[tenant] = st
    st["used"] = time.monotonic()
    return st


class _Busy(Exception):
    """The global browser cap is held - the envelope says so honestly."""


class _NoPage(Exception):
    """No tab is open for this tenant yet."""


def _current_page(st: dict) -> Page:
    if not st["pages"] or st["current"] < 0 or st["current"] >= len(st["pages"]):
        raise _NoPage()
    return st["pages"][st["current"]]


def _wire_page(st: dict, page: Page) -> None:
    page.on("console", st["on_console"])
    page.on("pageerror", st["on_pageerror"])
    page.on("close", st["on_close"])


def _safe_tenant(tenant_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", str(tenant_id or "x"))[:48] or "x"


# ---------------------------------------------------------------- the snapshot (tree + text + refs)

def _build_snapshot(st: dict, walk: list[dict]) -> dict:
    """One walk -> the tree lines, the refs map, the honest truncated flag."""
    counts: dict[tuple[str, str], int] = {}
    lines: list[str] = []
    refs: dict[str, dict] = {}
    for w in walk:
        key = (w["role"], w["name"])
        nth = counts.get(key, 0)
        counts[key] = nth + 1
        ref = f"e{len(lines) + 1}"
        extra = ""
        if w["role"] == "link" and w["href"]:
            extra = f' href={w["href"][:100]}'
        if w["role"] == "heading" and w["level"]:
            extra += f" [level={w['level']}]"
        if w["value"]:
            extra += f' value="{_clean(w["value"], 60)}"'
        if w["disabled"]:
            extra += " [disabled]"
        lines.append(f'{"  " * w["depth"]}- {w["role"]} "{w["name"]}" [ref={ref}]{extra}'.strip())
        if w["role"] in _ROLE_OK:
            kind = ("select" if w["role"] in ("combobox", "listbox") else
                    "fill" if (w["editable"] or w["role"] in _FILL_ROLES) else "click")
            refs[ref] = {"role": w["role"], "name": w["name"], "nth": nth, "tag": w["tag"],
                         "kind": kind}
    tree = "\n".join(lines)
    truncated = False
    if len(tree) > _MAX_TREE_CHARS:
        tree = tree[:_MAX_TREE_CHARS]
        truncated = True
    st["refs"], st["gen"] = refs, st["gen"] + 1
    return {"tree": tree, "refs": len(refs), "truncated": truncated}


async def _snapshot_page(st: dict, page: Page) -> dict:
    """The tree + the visible text of one page; tree and text are masked, navigation truth is not."""
    try:
        walk = await page.evaluate(_WALK_JS)
    except Exception as e:
        raise _PageGone(f"the page would not be read: {_clean(e, 140)}") from e
    snap = _build_snapshot(st, walk or [])
    try:
        text = await page.locator("body").inner_text(timeout=_STEP_TIMEOUT_MS)
    except Exception:
        text = ""
    text = " ".join(str(text or "").split())
    snap["truncated"] = snap["truncated"] or len(text) > _MAX_PAGE_TEXT
    snap["text"] = _mask_text(text[:_MAX_PAGE_TEXT])
    snap["tree"] = _mask_text(snap["tree"])
    try:
        snap["title"] = _clean(await page.title(), 200)
        snap["url"] = page.url[:_MAX_URL]
    except Exception:
        snap["title"], snap["url"] = "", ""
    return snap


class _PageGone(Exception):
    """The page crashed / navigated out from under the action."""


# ---------------------------------------------------------------- the actions (one envelope each)

async def _act_open(st: dict, url: str) -> dict:
    guarded = _guard_url(url)
    new_tab = False
    if not st["pages"] or st["current"] < 0:
        page = await st["context"].new_page()
        _wire_page(st, page)
        st["pages"].append(page)
        st["current"] = len(st["pages"]) - 1
        new_tab = True
    else:
        page = _current_page(st)
    try:
        await page.goto(guarded, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
    except Exception as e:
        raise _PageGone(f"the page did not open: {_clean(e, 140)}") from e
    try:
        await page.wait_for_load_state("load", timeout=3_000)
    except Exception:
        pass                                            # a slow asset never blocks the honest answer
    snap = await _snapshot_page(st, page)
    snap["new_tab"], snap["tab"] = new_tab, st["current"]
    return snap


async def _act_snapshot(st: dict) -> dict:
    page = _current_page(st)
    return await _snapshot_page(st, page)


def _locator_of(page: Page, meta: dict):
    loc = page.get_by_role(meta["role"], name=meta["name"], exact=True) if meta["name"] \
        else page.get_by_role(meta["role"])
    return loc.nth(meta["nth"])


async def _verify_ref(page: Page, meta: dict) -> None:
    """The ref must still be the same element: present, and the same tag. Else the page changed."""
    loc = _locator_of(page, meta)
    if await loc.count() == 0:
        raise _StaleRef(f"ref on '{meta['role']}' is not on the page any more")
    tag = await loc.evaluate(_TAG_JS)
    if tag != meta["tag"]:
        raise _StaleRef(f"the page changed under that ref (was a {meta['tag']}, now a {tag})")


async def _act_click(st: dict, ref: str) -> dict:
    page = _current_page(st)
    meta = st["refs"].get(str(ref or "").strip())
    if meta is None:
        raise _StaleRef(f"unknown or stale ref '{_clean(ref, 20)}'")
    await _verify_ref(page, meta)
    try:
        await _locator_of(page, meta).click(timeout=_STEP_TIMEOUT_MS)
    except _StaleRef:
        raise
    except Exception as e:
        raise _PageGone(f"the click did not land: {_clean(e, 140)}") from e
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=10_000)
    except Exception:
        pass
    snap = await _snapshot_page(st, page)
    snap["clicked"] = f"{meta['role']} \"{meta['name']}\" [ref={ref}]"
    snap["tab"] = st["current"]
    return snap


async def _act_type(st: dict, ref: str, text: str, submit: bool) -> dict:
    page = _current_page(st)
    meta = st["refs"].get(str(ref or "").strip())
    if meta is None:
        raise _StaleRef(f"unknown or stale ref '{_clean(ref, 20)}'")
    if meta["kind"] not in ("fill", "select"):
        raise _RefKind(f"ref {ref} is a {meta['kind']} target ('{meta['role']}'), not a field to type into")
    if len(text) > _MAX_TEXT_ARG:
        raise _TooBig(f"type caps one call at {_MAX_TEXT_ARG} chars")
    await _verify_ref(page, meta)
    loc = _locator_of(page, meta)
    try:
        if meta["kind"] == "select":
            try:
                await loc.select_option(label=text, timeout=_STEP_TIMEOUT_MS)
            except Exception:
                await loc.select_option(value=text, timeout=_STEP_TIMEOUT_MS)
        else:
            await loc.fill(text, timeout=_STEP_TIMEOUT_MS)
        if submit:
            await page.keyboard.press("Enter")
    except (_StaleRef, _TooBig, _RefKind):
        raise
    except Exception as e:
        raise _PageGone(f"the field did not take the text: {_clean(e, 140)}") from e
    snap = await _snapshot_page(st, page)
    snap["typed"] = {"ref": ref, "chars": len(text), "submit": bool(submit)}
    snap["tab"] = st["current"]
    return snap


async def _act_press(st: dict, key: str) -> dict:
    page = _current_page(st)
    key = str(key or "").strip()
    if key not in _PRESS_KEYS and not _PRESS_ONE.match(key):
        raise _BadKey(f"'{key[:20]}' is not a key this lane sends; named keys: "
                      f"{', '.join(sorted(_PRESS_KEYS))} - or ONE character")
    try:
        await page.keyboard.press(key)                  # the keyboard API takes no timeout - it never blocks
    except Exception as e:
        raise _PageGone(f"the key did not land: {_clean(e, 140)}") from e
    snap = await _snapshot_page(st, page)
    snap["pressed"] = key
    snap["tab"] = st["current"]
    return snap


async def _act_console(st: dict, clear: bool) -> dict:
    page = _current_page(st)
    rows = [{"type": r["type"], "text": _mask_text(r["text"]), "at": r["at"]} for r in st["con"]]
    if clear:
        st["con"].clear()
    return {"rows": rows[-_MAX_CON:], "shown": min(len(rows), _MAX_CON), "cleared": bool(clear),
            "tab": st["current"], "url": page.url[:_MAX_URL]}


async def _act_tabs(st: dict, op: str, index: Any, url: str) -> dict:
    op = str(op or "list").strip().lower()
    if op == "list":
        rows = []
        for i, p in enumerate(st["pages"]):
            try:
                rows.append({"index": i, "url": p.url[:_MAX_URL], "title": _clean(await p.title(), 120),
                             "current": i == st["current"]})
            except Exception:
                rows.append({"index": i, "url": "", "title": "", "current": i == st["current"]})
        return {"op": "list", "tabs": rows, "count": len(rows), "tab": st["current"]}
    if op == "new":
        if len(st["pages"]) >= _MAX_TABS:
            raise _TooBig(f"this browser holds {_MAX_TABS} tabs already (the RAM law) - close one first")
        guarded = _guard_url(url) if str(url or "").strip() else "about:blank"
        page = await st["context"].new_page()
        _wire_page(st, page)
        st["pages"].append(page)
        st["current"] = len(st["pages"]) - 1
        try:
            await page.goto(guarded, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
        except Exception as e:
            raise _PageGone(f"the new tab did not open: {_clean(e, 140)}") from e
        try:
            await page.wait_for_load_state("load", timeout=3_000)
        except Exception:
            pass
        snap = await _snapshot_page(st, page)
        snap["op"], snap["tab"], snap["opened"] = "new", st["current"], guarded[:_MAX_URL]
        return snap
    if op == "select":
        try:
            i = int(index)
        except (TypeError, ValueError):
            raise _BadIndex("give the tab index exactly as tabs=list showed it")
        if i < 0 or i >= len(st["pages"]):
            raise _BadIndex(f"no tab {i} - this browser holds {len(st['pages'])} tab(s)")
        st["current"] = i
        page = st["pages"][i]
        try:
            await page.bring_to_front()
        except Exception:
            pass
        snap = await _snapshot_page(st, page)
        snap["op"], snap["tab"] = "select", i
        return snap
    if op == "close":
        try:
            i = int(index) if index is not None else st["current"]
        except (TypeError, ValueError):
            raise _BadIndex("give the tab index exactly as tabs=list showed it")
        if i < 0 or i >= len(st["pages"]):
            raise _BadIndex(f"no tab {i} - this browser holds {len(st['pages'])} tab(s)")
        page = st["pages"][i]
        try:
            await page.close()
        except Exception:
            pass
        st["pages"] = [p for p in st["pages"] if p is not page]
        if not st["pages"]:
            n = await _close_tenant(_tenant_of(st))
            return {"op": "close", "closed": "the last tab - the browser is shut", "pages_closed": n}
        st["current"] = min(max(0, st["current"]), len(st["pages"]) - 1)
        snap = await _snapshot_page(st, st["pages"][st["current"]])
        snap["op"], snap["tab"], snap["closed_index"] = "close", st["current"], i
        snap["count"] = len(st["pages"])
        return snap
    raise _BadOp(f"unknown tabs op '{op[:20]}'; valid: list | select | new | close")


def _tenant_of(st: dict) -> str:
    with _TEN_LOCK:
        for t, s in _TENANTS.items():
            if s is st:
                return t
    return ""


async def _act_screenshot(tenant: str, st: dict, full: bool) -> dict:
    page = _current_page(st)
    d = Path("data") / _TENANT_DIR / _safe_tenant(tenant)
    d.mkdir(parents=True, exist_ok=True)
    st["seq"] = st.get("seq", 0) + 1
    name = f"shot-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{st['seq'] % 1000:03d}.png"
    p = d / name
    try:
        await page.screenshot(path=str(p), full_page=bool(full), timeout=15_000)
    except Exception as e:
        raise _PageGone(f"the picture did not happen: {_clean(e, 140)}") from e
    size = p.stat().st_size if p.exists() else 0
    if size > _MAX_SHOT_BYTES:
        try:
            p.unlink()
        except OSError:
            pass
        raise _TooBig(f"the page's picture is {size} bytes - over the {_MAX_SHOT_BYTES} cap; "
                      "screenshot the viewport (full=false) instead")
    return {"file": f"{_TENANT_DIR}/{_safe_tenant(tenant)}/{name}", "bytes": size,
            "full": bool(full), "tab": st["current"], "url": page.url[:_MAX_URL]}


async def _act_close(st: dict) -> dict:
    n = await _close_tenant(_tenant_of(st))
    return {"closed": True, "pages_closed": n}


# ---------------------------------------------------------------- the honest error wall

class _StaleRef(Exception):
    pass


class _RefKind(Exception):
    pass


class _TooBig(Exception):
    pass


class _BadKey(Exception):
    pass


class _BadIndex(Exception):
    pass


class _BadOp(Exception):
    pass


def _error_of(e: Exception) -> tuple[str, str, str]:
    if isinstance(e, _StaleRef):
        return (NOT_FOUND, str(e), "refs live until the page changes; action=snapshot first")
    if isinstance(e, _RefKind):
        return (BAD_INPUT, str(e), "take a fresh snapshot and pick a field ref (textbox / searchbox / combobox)")
    if isinstance(e, _TooBig):
        return (TOO_BIG, str(e), "the cap is the law; split the ask")
    if isinstance(e, _BadKey):
        return (BAD_INPUT, str(e), "one named key or one character, no chords")
    if isinstance(e, _BadIndex):
        return (NOT_FOUND, str(e), "action=tabs op=list shows the indexes")
    if isinstance(e, _BadOp):
        return (BAD_INPUT, str(e), "list | select | new | close")
    if isinstance(e, _NoPage):
        return (NOT_FOUND, "no page is open in this browser yet",
                "action=open with a url first (about:blank works)")
    if isinstance(e, _Busy):
        return (BUSY, "every allowed browser is busy with another tenant right now",
                f"the server keeps at most {_MAX_BROWSERS} tenant browsers alive (the RAM law); try again shortly")
    if isinstance(e, _PageGone):
        return (BROWSER_ERROR, str(e), "open the page again (action=open); the browser survives")
    if isinstance(e, ToolError):
        return (BLOCKED, str(e), "the guard only opens public http(s) pages (plus about:blank / data:text/html)")
    if isinstance(e, ValueError):
        return (BAD_INPUT, str(e), "name the argument the message points at")
    return (BROWSER_ERROR, f"the browser lane failed: {_clean(e, 160)}",
            "try the action again; if it repeats, action=close and start fresh")


# ================================================================ the ONE tool

async def jharokha(ctx: Ctx, action: str = "snapshot", *, url: str | None = None,
                   ref: str | None = None, text: str | None = None, key: str | None = None,
                   op: str | None = None, index: int | None = None, full: bool = False,
                   clear: bool = False, submit: bool = False, **_) -> dict:
    """The tenant's own headless browser. Never raises; every answer is one envelope."""
    started = time.monotonic()
    action = str(action or "").strip().lower()
    tenant = str(ctx.tenant_id or "")
    if action not in _JH_ACTIONS:
        return _jh_bad(action or "", f"unknown action '{action}'; valid: {', '.join(_JH_ACTIONS)}")
    if (lock := _locked(action)) is not None:
        return lock
    try:
        res = await _owned(_drive(tenant, action, url=url, ref=ref, text=text, key=key, op=op,
                                  index=index, full=full, clear=clear, submit=submit))
        out = _jh_envelope(action, **res) if isinstance(res, dict) else _jh_envelope(action)
    except Exception as e:
        out = _jh_envelope(action, error=_error_of(e))
    out["meta"]["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    return out


async def _drive(tenant: str, action: str, *, url, ref, text, key, op, index, full, clear, submit) -> dict:
    """The whole action on the owner loop, serialized per tenant - one browser, one hand at a time."""
    lk = _LOCKS.setdefault(tenant, asyncio.Lock())
    async with lk:
        await _reap_once()
        if action == "close":                           # close never launches a browser just to shut one
            with _TEN_LOCK:
                st = _TENANTS.get(tenant)
                if st is None or st.get("dropped"):
                    return {"closed": False, "pages_closed": 0,
                            "note": "no browser was open - nothing to close"}
            n = await _close_tenant(tenant)
            return {"closed": True, "pages_closed": n}
        st = await _get_tenant(tenant)
        try:
            if action == "open":
                if not str(url or "").strip():
                    raise ValueError("open needs a url (about:blank works)")
                return await _act_open(st, str(url))
            if action == "snapshot":
                return await _act_snapshot(st)
            if action == "click":
                return await _act_click(st, str(ref or ""))
            if action == "type":
                return await _act_type(st, str(ref or ""), str(text or ""), bool(submit))
            if action == "press":
                return await _act_press(st, str(key or ""))
            if action == "console":
                return await _act_console(st, bool(clear))
            if action == "tabs":
                return await _act_tabs(st, str(op or "list"), index, str(url or ""))
            if action == "screenshot":
                return await _act_screenshot(tenant, st, bool(full))
            raise _BadOp(f"unknown action '{action}'")
        finally:
            st["used"] = time.monotonic()


# ---------------------------------------------------------------- the tool spec the model sees
JHAROKHA_TOOLS = [
    {"name": "jharokha", "description": (
        "JHAROKHA MANCH (v0.665): the agent's OWN headless Chromium, driven one deterministic action "
        "at a time - the T3 local-browser idea, zero login, zero key. Actions: open (navigate the "
        "current tab, SSRF-guarded public http(s) plus about:blank / data:text/html scratch pages) | "
        "snapshot (the page's interactive tree with refs e1, e2... + its visible text - a fresh "
        "snapshot rides EVERY answer, and refs live only until the page changes) | click (ONE real "
        "click through a ref) | type (fill a textbox / searchbox / combobox by ref, submit=true "
        "presses Enter after) | press (ONE named key: Enter, Tab, Escape, Backspace, Delete, arrows, "
        "Home/End/PageUp/PageDown/Space, or one character) | console (this browser's own console tail "
        "- page logs + uncaught errors; clear=true empties) | tabs (list | select | new | close, "
        "capped) | screenshot (ONE PNG saved into this tenant's files, path + bytes back, never "
        "base64) | close (shut this browser now - RAM hygiene). Ephemeral and clean: no profile, no "
        "cookies on disk, nothing shared across tenants. No evaluate, no downloads, no file://, no "
        "credentials - the agentic door for those is the Computer Operator, not this lane. One "
        "envelope {ok, action, error:{code, message, hint}}."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": list(_JH_ACTIONS),
                    "description": "open | snapshot | click | type | press | console | tabs | screenshot | close"},
         "url": {"type": "string", "description": "open / tabs new: the page to load (public http(s), about:blank, or a short data:text/html scratch page)"},
         "ref": {"type": "string", "description": "click / type: the element ref from the last snapshot (e.g. 'e5')"},
         "text": {"type": "string", "description": "type: the text to fill (or the option's label for a combobox)"},
         "key": {"type": "string", "description": "press: one named key (Enter, Tab, Escape, ...) or one character"},
         "op": {"type": "string", "description": "tabs: list | select | new | close"},
         "index": {"type": "integer", "description": "tabs select / close: the tab index from tabs=list"},
         "full": {"type": "boolean", "description": "screenshot: full_page picture (default false = the viewport)"},
         "clear": {"type": "boolean", "description": "console: clear=true empties the tail after reading"},
         "submit": {"type": "boolean", "description": "type: press Enter after filling"}}}},
]

JHAROKHA_LABELS = {"jharokha": "Jharokha: the agent's own local browser window"}
JHAROKHA_HANDLERS = {"jharokha": jharokha}

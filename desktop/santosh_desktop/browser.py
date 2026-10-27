"""Hoola reads her browser like a person: the page's exact words, the open tabs, what a field really contains,
and what actually finished downloading.

v1.4 Windows UI Automation (UIA): Chrome / Edge / Firefox expose the whole page as an accessibility tree, so
Hoola can read labels, prices, buttons and tab titles EXACTLY — no screenshot guessing, no extra vision step.
Everything here degrades quietly: on another OS, or when the browser hides its tree, the PC operator simply
keeps working on screenshots like before. Nothing here types or clicks by itself and no field VALUE is ever
returned to the server (only lengths and a matches true/false), so typed numbers stay as private as before.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    import uiautomation as ua          # Windows only (requirements pins it to win32)
except Exception:
    ua = None

# control types whose Name carries meaningful page text (UIA ControlTypeName strings)
TEXT_TYPES = {"TextControl", "DocumentControl", "HyperlinkControl", "ListItemControl", "ButtonControl",
              "ComboBoxControl", "HeaderControl", "TableControl", "DataItemControl", "ImageControl"}
WALK_BUDGET = 240      # UIA nodes visited per read (each node is a COM call: ~1.5–3 s total, cheap vs a vision step)
WALK_DEPTH = 11


class BrowserUnavailable(Exception):
    """The browser cannot be read right now (not Windows, no UIA, no browser window)."""


def available() -> bool:
    return sys.platform == "win32" and ua is not None


# ---------------- windows ----------------
def _browser_windows() -> list:
    """Top-level windows that belong to a real browser (Chrome / Edge / Brave / Firefox)."""
    if not available():
        return []
    out = []
    try:
        for c in ua.GetRootControl().GetChildren():
            cls = getattr(c, "ClassName", "") or ""
            if cls in ("Chrome_WidgetWin_1", "MozillaWindowClass"):
                out.append(c)
    except Exception:
        pass
    return out or []


def _active_browser():
    """The browser window in front right now, else any open browser window."""
    if not available():
        return None
    try:
        fg = ua.GetForegroundControl()
    except Exception:
        fg = None
    wins = _browser_windows()
    if fg is not None and any(fg is w for w in wins):
        return fg
    return wins[0] if wins else None


# ---------------- page text ----------------
def page_text(max_chars: int = 6000) -> dict[str, Any]:
    """The words on the page open in her browser, in order (title + url + text)."""
    win = _active_browser()
    if win is None:
        raise BrowserUnavailable("No browser window is open right now (Chrome / Edge / Firefox).")
    title = (win.Name or "").strip()
    lines: list[str] = []
    budget = {"n": WALK_BUDGET}

    def walk(c, d: int) -> None:
        if budget["n"] <= 0 or d > WALK_DEPTH or len(lines) > 500:
            return
        budget["n"] -= 1
        try:
            t = c.ControlTypeName
            name = (c.Name or "").strip()
        except Exception:
            return
        if t in TEXT_TYPES and len(name) > 1:
            lines.append(name)
        if t in ("EditControl", "ComboBoxControl"):     # leaf-ish: do not descend (saves COM calls)
            return
        try:
            kids = c.GetChildren()
        except Exception:
            return
        for k in kids[:60]:
            walk(k, d + 1)

    doc = None
    try:
        doc = win.DocumentControl(searchDepth=6, timeout=0.6)   # the web page itself, when exposed
    except Exception:
        doc = None
    walk(doc or win, 0)
    out, prev = [], None
    for ln in lines:
        ln = re.sub(r"\s+", " ", ln).strip()
        if ln and ln != prev:
            out.append(ln)
        prev = ln
    return {"title": title[:200], "url": _url_of(win), "text": "\n".join(out)[:max(500, int(max_chars or 6000))],
            "lines": len(out)}


def _url_of(win) -> str:
    """The address-bar URL (best effort; '' when the browser does not expose it)."""
    for name in ("Address and search bar", "Search with Google or enter address"):
        try:
            e = win.EditControl(Name=name, searchDepth=14, timeout=0.4)
            try:
                return (e.GetValuePattern().Value or "").strip()[:500]
            except Exception:
                return (e.Name or "").strip()[:500]
        except Exception:
            continue
    return ""


# ---------------- tabs ----------------
def tabs() -> dict[str, Any]:
    """The open tabs of the browser in front: number, title, which one is active."""
    win = _active_browser()
    if win is None:
        raise BrowserUnavailable("No browser window is open right now.")
    items: list = []

    def find(c, d: int) -> None:
        if d > 9 or len(items) > 40:
            return
        try:
            t = c.ControlTypeName
        except Exception:
            return
        if t == "TabItemControl":
            items.append(c)
            return
        try:
            kids = c.GetChildren()
        except Exception:
            return
        for k in kids[:40]:
            find(k, d + 1)

    find(win, 0)
    out = []
    for i, c in enumerate(items):
        try:
            name = (c.Name or "").strip()[:120]
        except Exception:
            name = ""
        active = False
        try:
            active = bool(c.GetSelectionItemPattern().IsSelected)
        except Exception:
            active = False
        out.append({"index": i + 1, "title": name, "active": active})
    return {"tabs": out, "count": len(out)}


def switch_tab(tab: str = "", index: int = 0) -> dict[str, Any]:
    """Move to a tab by (part of) its title, or by its 1-based number from tabs()."""
    ts = tabs()
    items = ts.get("tabs") or []
    if not items:
        raise BrowserUnavailable("No tabs visible in her browser.")
    pick: dict[str, Any] | None = None
    q = (tab or "").strip().lower()
    if q:
        pick = next((t for t in items if q in (t.get("title") or "").lower()), None)
    if pick is None and index:
        pick = next((t for t in items if t.get("index") == int(index)), None)
    if pick is None:
        raise BrowserUnavailable(f"No tab matches '{(tab or index)[:60]}'. Call tabs first.")
    # re-find the live control by position and select it (controls die between calls)
    live: list = []
    win = _active_browser()
    if win is not None:
        def find(c, d: int) -> None:
            if d > 9 or len(live) > 40:
                return
            try:
                if c.ControlTypeName == "TabItemControl":
                    live.append(c)
                    return
            except Exception:
                return
            try:
                kids = c.GetChildren()
            except Exception:
                return
            for k in kids[:40]:
                find(k, d + 1)
        find(win, 0)
    i = pick["index"] - 1
    if i >= len(live):
        raise BrowserUnavailable("The tab strip changed; call tabs again.")
    c = live[i]
    done = False
    for call in (lambda: c.GetSelectionItemPattern().Select(), lambda: c.GetInvokePattern().Invoke(),
                 lambda: c.Click(simulateMove=False)):
        try:
            call()
            done = True
            break
        except Exception:
            continue
    if not done:
        raise BrowserUnavailable("Could not switch to that tab.")
    time.sleep(0.6)
    after = tabs()
    title = ""
    for t in after.get("tabs") or []:
        if t.get("active"):
            title = t.get("title") or ""
            break
    return {"switched": pick.get("title", ""), "title": title, "tabs": after.get("tabs")}


# ---------------- typed-value check ----------------
def verify_typed(expected: str) -> dict[str, Any]:
    """Does the focused field really contain what was just typed? PRIVACY: only the length and a true/false
    come back — never the field's value (so an ID number typed from the Locker stays hidden from the model)."""
    if not available():
        return {}
    try:
        c = ua.GetFocusedControl()
    except Exception:
        return {}
    if c is None:
        return {}
    try:
        kind = c.ControlTypeName
    except Exception:
        return {}
    if kind not in ("EditControl", "ComboBoxControl", "DocumentControl"):
        return {}
    val = ""
    try:
        val = c.GetValuePattern().Value or ""
    except Exception:
        try:
            val = c.Name or ""
        except Exception:
            val = ""
    norm = lambda s: re.sub(r"\s+", " ", s or "").strip()
    got, want = norm(val), norm(expected)
    if not want:
        return {}
    return {"kind": kind, "length": len(val), "matches": got == want or got.endswith(want)}


# ---------------- downloads ----------------
PARTIAL_EXT = (".crdownload", ".part", ".tmp")


# ---------------- v1.5.0 SEMANTIC ACTIONS (UIA): act on page elements by ref, not by guessed pixels --------
# The operator's root pain: the model guesses X,Y on a JPEG and pyautogui clicks - misses on layout shift
# / DPI, one slow vision round trip per step. The accessibility tree already carries the REAL elements
# (browser.py reads it since v1.4); now it also ACTS on them: page_elements -> page_click / page_type /
# page_select / page_fill_form by ref. The OS resolves the element; the click cannot miss on coordinates.
INTERACTIVE = ("ButtonControl", "HyperlinkControl", "EditControl", "ComboBoxControl",
               "CheckBoxControl", "RadioButtonControl", "TabItemControl", "MenuItemControl", "SummaryControl")
_ROLE = {"ButtonControl": "button", "HyperlinkControl": "link", "EditControl": "input",
         "ComboBoxControl": "select", "CheckBoxControl": "checkbox", "RadioButtonControl": "radio",
         "TabItemControl": "tab", "MenuItemControl": "menuitem", "SummaryControl": "button"}
_REFS: list[dict[str, str]] = []       # ref -> {"type": ControlTypeName, "name": Name} from the last page_elements


def _iter_interactive(win, out: list, budget: dict) -> None:
    """Depth-first walk collecting VISIBLE interactive controls (same shape as page_text's walk)."""
    if budget["n"] <= 0 or len(out) >= 300:
        return
    budget["n"] -= 1
    try:
        t = win.ControlTypeName
        name = (win.Name or "").strip()
    except Exception:
        return
    if t in INTERACTIVE and len(name) > 0:
        out.append({"type": t, "name": name[:90]})
    if t in ("EditControl", "ComboBoxControl"):     # leaf-ish: no descent (saves COM calls)
        return
    try:
        kids = win.GetChildren()
    except Exception:
        return
    for k in kids[:60]:
        _iter_interactive(k, out, budget)


def _refind(kind: str, name: str, nth: int = 0):
    """Re-find a live control by (ControlTypeName, Name, occurrence #) - controls die between calls
    (same lesson as switch_tab), so refs are re-walked at action time, never cached as objects."""
    win = _active_browser()
    if win is None:
        raise BrowserUnavailable("No browser window is open right now.")
    hits: list = []
    budget = {"n": 400}

    def walk(c, d: int) -> None:
        if budget["n"] <= 0 or len(hits) > nth + 4 or d > WALK_DEPTH:
            return
        budget["n"] -= 1
        try:
            if c.ControlTypeName == kind and (c.Name or "").strip() == name:
                hits.append(c)
                return
        except Exception:
            return
        try:
            kids = c.GetChildren()
        except Exception:
            return
        for k in kids[:60]:
            walk(k, d + 1)

    walk(win, 0)
    if nth >= len(hits):
        return None
    return hits[nth]


def page_elements(max_items: int = 60) -> dict[str, Any]:
    """The page's clickable / typeable elements as a numbered list (ref, role, visible name).
    THE exact way to act: refs go to page_click / page_type / page_select / page_fill_form."""
    global _REFS
    win = _active_browser()
    if win is None:
        raise BrowserUnavailable("No browser window is open right now (Chrome / Edge / Firefox).")
    raw: list = []
    _iter_interactive(win, raw, {"n": 400})
    _REFS = raw[:max(1, min(int(max_items or 60), 200))]
    elements = [{"ref": i, "role": _ROLE.get(e["type"], e["type"]), "name": e["name"]}
                for i, e in enumerate(_REFS, 1)]
    return {"title": (win.Name or "")[:200], "url": _url_of(win), "count": len(elements), "elements": elements}


def page_click(ref: int) -> dict[str, Any]:
    """Click a page element BY REF (Invoke / Toggle / Expand / Select patterns, else a click at the
    control's own centre - OS-computed, never a model-guessed pixel)."""
    i = int(ref or 0)
    if not 1 <= i <= len(_REFS):
        raise BrowserUnavailable(f"ref {ref} gaya - pehle page_elements dobara chalao.")
    e = _REFS[i - 1]
    c = _refind(e["type"], e["name"])
    if c is None:
        raise BrowserUnavailable("Element ab nahi mila (page badla?) - page_elements dobara chalao.")
    done = False
    for call in (lambda: c.GetInvokePattern().Invoke(), lambda: c.GetTogglePattern().Toggle(),
                 lambda: c.GetExpandCollapsePattern().Expand(), lambda: c.GetSelectionItemPattern().Select(),
                 lambda: c.Click(simulateMove=False)):
        try:
            call()
            done = True
            break
        except Exception:
            continue
    if not done:
        raise BrowserUnavailable("Element par koi action nahi chala ( Invoke/Toggle/Click sab fail).")
    time.sleep(0.8)
    after = _active_browser()
    return {"clicked": True, "title": (after.Name or "")[:200] if after else ""}


def page_type(ref: int, text: str = "", clear: bool = True) -> dict[str, Any]:
    """Type into a page field BY REF. ValuePattern first (fast + fires real events in Chromium/Edge),
    clipboard paste as fallback. PRIVACY: only length + matches come back, never the value."""
    from .control import paste_text
    i = int(ref or 0)
    if not 1 <= i <= len(_REFS):
        raise BrowserUnavailable(f"ref {ref} gaya - pehle page_elements dobara chalao.")
    e = _REFS[i - 1]
    c = _refind(e["type"], e["name"])
    if c is None:
        raise BrowserUnavailable("Field ab nahi mila (page badla?) - page_elements dobara chalao.")
    val = ""
    try:
        c.SetFocus()
    except Exception:
        pass
    if clear:
        try:
            c.GetValuePattern().SetValue("")
        except Exception:
            pass
    ok = False
    try:
        c.GetValuePattern().SetValue(text or "")
        ok = True
    except Exception:
        try:
            paste_text(text or "")
            ok = True
        except Exception:
            ok = False
    try:
        val = c.GetValuePattern().Value or ""
    except Exception:
        val = ""
    got = re.sub(r"\s+", " ", val).strip()
    want = re.sub(r"\s+", " ", text or "").strip()
    return {"typed": ok, "length": len(val), "matches": (got == want or got.endswith(want)) if want else bool(ok)}


def page_select(ref: int, value: str = "") -> dict[str, Any]:
    """Pick an option BY REF in a dropdown/combobox (expand, then select the matching item)."""
    i = int(ref or 0)
    if not 1 <= i <= len(_REFS):
        raise BrowserUnavailable(f"ref {ref} gaya - pehle page_elements dobara chalao.")
    e = _REFS[i - 1]
    c = _refind(e["type"], e["name"])
    if c is None:
        raise BrowserUnavailable("Dropdown ab nahi mila - page_elements dobara chalao.")
    want = re.sub(r"\s+", " ", (value or "")).strip().lower()
    try:
        c.GetExpandCollapsePattern().Expand()
        time.sleep(0.4)
    except Exception:
        pass
    opts: list = []
    budget = {"n": 120}

    def find_items(p, d: int) -> None:
        if budget["n"] <= 0 or len(opts) > 40 or d > 6:
            return
        budget["n"] -= 1
        try:
            if p.ControlTypeName == "ListItemControl":
                opts.append(p)
                return
        except Exception:
            return
        try:
            kids = p.GetChildren()
        except Exception:
            return
        for k in kids[:40]:
            find_items(k, d + 1)

    find_items(c, 0)
    for o in opts:
        try:
            nm = re.sub(r"\s+", " ", (o.Name or "")).strip()
        except Exception:
            continue
        if want and (nm.lower() == want or want in nm.lower()):
            for call in (lambda: o.GetSelectionItemPattern().Select(), lambda: o.GetInvokePattern().Invoke(),
                         lambda: o.Click(simulateMove=False)):
                try:
                    call()
                    return {"selected": nm[:90]}
                except Exception:
                    continue
    return {"selected": "", "options": [ (o.Name or "")[:60] for o in opts[:20] ]}


def page_fill_form(entries: list) -> dict[str, Any]:
    """Many fields in ONE step: entries = [{'ref': 2, 'text': '...'}, ...]."""
    out = []
    for it in (entries or [])[:20]:
        try:
            r = page_type(int(it.get("ref") or 0), str(it.get("text") or ""), clear=True)
            out.append({"ref": it.get("ref"), **r})
        except BrowserUnavailable as e:
            out.append({"ref": it.get("ref"), "typed": False, "err": str(e)[:120]})
    return {"filled": sum(1 for x in out if x.get("typed")), "total": len(out), "results": out}


def wait_for(text: str = "", seconds: int = 15) -> dict[str, Any]:
    """Wait until a text appears in her browser's page (polls the UIA tree; max 20s)."""
    want = re.sub(r"\s+", " ", (text or "")).strip().lower()
    if not want:
        raise BrowserUnavailable("Kis text ka intezaar?")
    end = time.time() + max(2, min(int(seconds or 15), 20))
    while time.time() < end:
        try:
            body = re.sub(r"\s+", " ", (page_text(4000).get("text") or "")).lower()
            if want in body:
                return {"found": True}
        except BrowserUnavailable:
            pass
        time.sleep(1.0)
    return {"found": False, "note": f"'{want[:60]}' {int(seconds or 15)}s mein nahi dikha"}


def downloads(minutes: int = 15, limit: int = 20) -> dict[str, Any]:
    """What actually landed in her Downloads folder recently — and what is STILL downloading."""
    home = Path.home()
    folder = next((home / n for n in ("Downloads", "downloads") if (home / n).is_dir()), None)
    if folder is None:
        return {"folder": "", "files": [], "note": "Downloads folder not found on this PC."}
    cutoff = time.time() - max(1, min(int(minutes or 15), 720)) * 60
    found: list[tuple[float, Path, int]] = []
    try:
        for c in folder.iterdir():
            try:
                if c.is_file() and not c.name.startswith((".", "~$")):
                    st = c.stat()
                    if st.st_mtime >= cutoff:
                        found.append((st.st_mtime, c, st.st_size))
            except OSError:
                continue
    except OSError as e:
        return {"folder": str(folder), "files": [], "note": f"Could not read the folder ({e})"}
    found.sort(key=lambda x: -x[0])
    files = []
    for m, c, size in found[:max(1, min(int(limit or 20), 50))]:
        files.append({"name": c.name, "size": size,
                      "size_text": f"{size // 1024} KB" if size < 50 * 1024 * 1024 else f"{size // (1024 * 1024)} MB",
                      "partial": c.name.lower().endswith(PARTIAL_EXT),
                      "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(m))})
    return {"folder": str(folder), "files": files, "count": len(files)}

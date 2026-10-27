"""Hoola PC agent: the Linux cloud computer that belongs to Hoola (the coworker's own PC).

Speaks the SAME wire protocol as the Windows Santosh Desktop (server/app/pc/hub.py):
  dials out to the server over WebSocket, answers {"type": "info"}, runs {"type": "job"} messages,
  replies {"type": "result", "id", ok, data|error}. The PC operator (pc/operator.py) drives this
  PC exactly like her Windows PC - the vision loop cannot tell the difference.

The difference is what this PC IS: an Ubuntu container Hoola owns (Xvfb + openbox + Chromium).
So it gets extra actions the user's PC never offers:
  install    - apt-get / pip install packages (this is Hoola's own VM; no approval needed)
  run        - run a shell command inside the VM (the Claude-harness bash tool, same trust model)
  send_file  - v0.202 upload one of MY files to the server tagged direction "to_pc", so the USER'S
               personal PC can fetch it into her Santosh Inbox (the PC-to-PC file bridge; the server
               shows her a confirm card before it lands on her PC)

Browser intelligence goes over the Chrome DevTools Protocol (Chromium started lazily with
--remote-debugging-port=9222), NOT screen scraping: page_text / tabs / switch_tab / open_url
are exact. Screen + mouse + keyboard are Xvfb + xdotool + scrot, like the Anthropic reference
computer-use image.

State lives in /data (a Docker volume): identity.json (device_id + token), chrome profile
(logged-in sessions survive restarts), Downloads, installed.log.
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import platform
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import httpx

DATA = Path(os.environ.get("HOOLA_DATA", "/data"))
SERVER = os.environ.get("HOOLA_SERVER", "http://127.0.0.1:8077").strip().rstrip("/")
NAME = os.environ.get("HOOLA_PC_NAME", "Hoola PC")
DISPLAY = os.environ.get("DISPLAY", ":1")
CDP = "http://127.0.0.1:9222"
VERSION = "1.3.0"
MAX_SEND = 50 * 1024 * 1024   # same upload cap as the Windows Santosh Desktop
DOWNLOADS = DATA / "Downloads"
PROFILE = DATA / "chrome"
SHOT_DIR = Path("/tmp")

for _d in (DATA, DOWNLOADS, PROFILE):
    _d.mkdir(parents=True, exist_ok=True)


class ActionError(Exception):
    pass


# ---------------- pairing + identity ----------------
def _identity() -> dict[str, str]:
    f = DATA / "identity.json"
    if f.exists():
        try:
            d = json.loads(f.read_text())
            if d.get("device_id") and d.get("token"):
                return d
        except ValueError:
            pass
    return {}


def _save_identity(device_id: str, token: str) -> None:
    (DATA / "identity.json").write_text(json.dumps({"device_id": device_id, "token": token}))


def pair_once(code: str) -> str:
    """Exchange the 6-digit code from her app (Mera PC > pair) for this PC's own token."""
    r = httpx.post(SERVER + "/api/pc/pair", json={"code": code.strip(), "name": NAME,
                                                  "os": "Linux (Hoola PC)"}, timeout=20)
    if r.status_code >= 400:
        raise ActionError(f"pair failed: {r.text[:160]}")
    d = r.json()
    _save_identity(d["device_id"], d["token"])
    return d["device_id"]


# ---------------- xdotool / wmctrl helpers ----------------
def _x(*args: str, timeout: float = 15) -> str:
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return (p.stdout or "").strip()


def _windows() -> list[str]:
    out = _x("wmctrl", "-l")
    titles = []
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4:
            titles.append(parts[3])
    return titles


def _active_window() -> str:
    try:
        return _x("xdotool", "getactivewindow", "getwindowname", timeout=5)
    except Exception:
        return ""


# ---------------- Chrome over CDP (lazy) ----------------
_chrome_lock = threading.Lock()
_chrome: subprocess.Popen | None = None


def _browser_exe() -> str:
    """v1.2.0 real Google Chrome first (full codecs H.264/AAC/MP3 + the build sites are tested
    against - Debian's chromium has no proprietary codecs and that is most of the 'Chromium has
    issues' pain: videos black, some media sites broken). chromium stays as the fallback."""
    for e in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if subprocess.run(["which", e], capture_output=True).returncode == 0:
            return e
    return "chromium"


def _chrome_up() -> None:
    global _chrome
    with _chrome_lock:
        if _chrome is not None and _chrome.poll() is None:
            try:
                httpx.get(CDP + "/json/version", timeout=2)
                return
            except Exception:
                pass
        # --no-sandbox: the container runs as root - Chrome refuses to start without it
        # (Debian's chromium wrapper adds it silently for root, Google Chrome does not).
        flags = ["--remote-debugging-port=9222", f"--user-data-dir={PROFILE}", "--no-first-run",
                 "--no-default-browser-check", "--disable-session-crashed-bubble", "--start-maximized",
                 "--window-position=0,0", "--window-size=1280,760", "--disable-dev-shm-usage",
                 "--disable-crash-reporter", "--force-device-scale-factor=1", "--password-store=basic",
                 "--no-sandbox"]
        exe = _browser_exe()
        # stderr to a file, not DEVNULL (v1.3.0 lesson: a chrome that will not boot was INVISIBLE -
        # the selftest could only say 'CDP ready nahi hua'; now the real error is in /tmp/chrome_err.log)
        _chrome = subprocess.Popen([exe, *flags], env={**os.environ, "DISPLAY": DISPLAY},
                                   stdout=subprocess.DEVNULL,
                                   stderr=open("/tmp/chrome_err.log", "ab"))
    for _ in range(90):          # up to ~45s for first paint (real Chrome on a big profile is slower
        try:                     # than 15s on its first boot - dbus/machine-id noise + profile work)
            httpx.get(CDP + "/json/version", timeout=2)
            return
        except Exception:
            time.sleep(0.5)
    raise ActionError("Chrome nahi khula (CDP ready nahi hua) - /tmp/chrome_err.log par dekho")


def _targets() -> list[dict[str, Any]]:
    r = httpx.get(CDP + "/json", timeout=5)
    return [t for t in r.json() if t.get("type") == "page"]


def _active_target() -> dict[str, Any]:
    ts = _targets()
    if not ts:
        raise ActionError("Koi page khula nahi hai")
    act = _active_window()
    for t in ts:
        if act and t.get("title") == act:
            return t
    return ts[0]


def _cdp_eval(t: dict[str, Any], expr: str, timeout: float = 15) -> Any:
    """One Runtime.evaluate over the page's WebSocket debugger."""
    import websockets

    async def go() -> Any:
        async with websockets.connect(t["webSocketDebuggerUrl"], max_size=16 * 1024 * 1024, open_timeout=10) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
                                      "params": {"expression": expr, "returnByValue": True,
                                                 "awaitPromise": True}}))
            end = time.time() + timeout
            while time.time() < end:
                raw = await asyncio.wait_for(ws.recv(), timeout=max(1, end - time.time()))
                msg = json.loads(raw)
                if msg.get("id") == 1:
                    return msg.get("result", {}).get("result", {}).get("value")
        return None

    return asyncio.run(go())


# ---------------- the actions ----------------
class Actions:
    def __init__(self) -> None:
        self.log = print
        self._els: dict[int, str] = {}          # v1.3.0 semantic refs: ref -> CSS selector of the element
        self._els_src: str = ""                 # title+url the refs were taken from (staleness check)

    def info(self) -> dict[str, Any]:
        return {"type": "info", "name": NAME, "os": f"Linux {platform.release()} (Hoola PC)",
                "version": VERSION, "kind": "hoola_pc",
                "folders": [{"path": str(DATA), "label": "Hoola PC"}],
                "tally": {}, "indexed": 0, "inbox": str(DOWNLOADS), "paused": False, "control": True}

    def handle(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        fn = getattr(self, "do_" + action, None)
        if fn is None:
            raise ActionError(f"Unknown action {action}")
        try:
            return fn(**(args or {}))
        except ActionError:
            raise
        except TypeError as e:
            raise ActionError(f"Bad request: {e}")
        except Exception as e:
            raise ActionError(f"{type(e).__name__}: {e}"[:300])

    # ---- screen + control (xdotool) ----
    def do_screen(self, max_width: int = 1280, monitor: str = "primary", **_) -> dict[str, Any]:
        p = SHOT_DIR / "hoola_pc_shot.png"
        _x("scrot", "-o", str(p), timeout=20)
        from PIL import Image
        img = Image.open(p).convert("RGB")
        w, h = img.size
        mw = max(320, min(int(max_width or 1280), 1920))
        if w > mw:
            img = img.resize((mw, round(h * mw / w)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=72)
        return {"image_b64": base64.b64encode(buf.getvalue()).decode(), "width": img.size[0],
                "height": img.size[1], "monitor": "primary", "active_window": _active_window(),
                "windows": _windows()[:12]}

    def do_control(self, op: str = "", x: Any = None, y: Any = None, text: str = "", keys: str = "",
                   amount: int = 0, to_x: Any = None, to_y: Any = None, **_) -> dict[str, Any]:
        op = str(op or "")
        if op in ("click", "right_click", "double_click"):
            xi, yi = int(x or 0), int(y or 0)
            if op == "right_click":
                _x("xdotool", "mousemove", str(xi), str(yi), "click", "3")
            elif op == "double_click":
                _x("xdotool", "mousemove", str(xi), str(yi), "click", "--repeat", "2", "--delay", "60", "1")
            else:
                _x("xdotool", "mousemove", str(xi), str(yi), "click", "1")
            return {"ok": True}
        if op == "type":
            text = str(text or "")[:4000]
            if not text:
                return {"ok": True}
            _x("xdotool", "type", "--clearmodifiers", "--delay", "10", "--", text, timeout=120)
            return {"ok": True}
        if op == "key":
            k = str(keys or "").strip()
            if not k:
                return {"ok": True}
            mapped = {"enter": "Return", "esc": "Escape", "win": "super", "del": "Delete"}.get(k.lower(), k)
            _x("xdotool", "key", "--", mapped)
            return {"ok": True}
        if op == "scroll":
            xi, yi = int(x or 640), int(y or 400)
            steps = max(1, min(abs(int(amount or -5)) * 2, 30))
            btn = "4" if int(amount or -5) > 0 else "5"          # 4 = up, 5 = down
            _x("xdotool", "mousemove", str(xi), str(yi), "click", "--repeat", str(steps), "--delay", "30", btn)
            return {"ok": True}
        if op == "drag":
            _x("xdotool", "mousemove", str(int(x or 0)), str(int(y or 0)), "mousedown", "1")
            _x("xdotool", "mousemove", "--sync", str(int(to_x or 0)), str(int(to_y or 0)))
            _x("xdotool", "mouseup", "1")
            return {"ok": True}
        raise ActionError(f"Unknown control op {op}")

    # ---- apps / windows ----
    _APPS = {"chrome": "@browser", "chromium": "@browser", "browser": "@browser", "files": "xdg-open",
             "calculator": "gnome-calculator", "text editor": "gedit", "editor": "gedit",
             "terminal": None, "cmd": None}

    def do_apps(self, **_) -> dict[str, Any]:
        apps = ["Chrome (Google Chrome)", "Files", "Text Editor (gedit)", "Calculator",
                "LibreOffice / anything installed via the install action"]
        return {"apps": apps, "windows": _windows()[:20]}

    def do_open_app(self, name: str = "", **_) -> dict[str, Any]:
        name = str(name or "").strip()
        low = name.lower()
        cmd = self._APPS.get(low)
        if cmd == "@browser":
            cmd = _browser_exe()          # v1.2.0 google-chrome when present, chromium otherwise
        if cmd is None and low in self._APPS:
            raise ActionError("Terminal yahan nahi khulta - run action use kijiye (yeh Hoola ka apna VM hai).")
        if cmd is None:
            for cand in (low, low.replace(" ", "-"), low.replace(" ", "_")):
                if subprocess.run(["which", cand], capture_output=True).returncode == 0:
                    cmd = cand
                    break
        if cmd is None:
            raise ActionError(f"{name} install nahi hai. Pehle install action se install kijiye.")
        args = [cmd, str(DATA)] if cmd == "xdg-open" else [cmd]
        subprocess.Popen(args, env={**os.environ, "DISPLAY": DISPLAY},
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.0)
        return {"opened": name}

    def do_focus(self, title: str = "", **_) -> dict[str, Any]:
        t = str(title or "")
        if subprocess.run(["wmctrl", "-a", t], capture_output=True, env={**os.environ, "DISPLAY": DISPLAY}).returncode != 0:
            raise ActionError(f"'{t}' naam ki koi window nahi mili")
        return {"focused": _active_window() or t}

    def do_window(self, op: str = "", title: str = "", **_) -> dict[str, Any]:
        op = str(op or "").lower()
        env = {**os.environ, "DISPLAY": DISPLAY}
        t = str(title or "")
        if op == "close":
            subprocess.run(["wmctrl", "-c", t], capture_output=True, env=env)
        elif op == "minimize":
            subprocess.run(["wmctrl", "-a", t], capture_output=True, env=env)
            subprocess.run(["xdotool", "getactivewindow", "windowminimize"], capture_output=True, env=env)
        elif op == "maximize":
            subprocess.run(["wmctrl", "-a", t], capture_output=True, env=env)
            subprocess.run(["wmctrl", "-r", t, "-b", "add,maximized_vert,maximized_horz"], capture_output=True, env=env)
        elif op == "restore":
            subprocess.run(["wmctrl", "-a", t], capture_output=True, env=env)
            subprocess.run(["wmctrl", "-r", t, "-b", "remove,maximized_vert,maximized_horz"], capture_output=True, env=env)
        else:
            raise ActionError("op must be minimize, maximize, restore or close")
        return {"window": _active_window() or t}

    # ---- browser intelligence over CDP ----
    def do_open_url(self, url: str = "", **_) -> dict[str, Any]:
        url = str(url or "").strip()
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        _chrome_up()
        r = httpx.put(CDP + f"/json/new?{url}", timeout=10)   # PUT is required on newer Chromium
        if r.status_code >= 400:
            r = httpx.put(CDP + "/json/new", params={"url": url}, timeout=10)
        t = r.json()
        tid = t.get("id", "")
        title = ""
        loaded = False
        end = time.time() + 12
        while time.time() < end:
            time.sleep(0.8)
            try:
                cur = next((x for x in _targets() if x.get("id") == tid), None)
            except Exception:
                cur = None
            if cur is None:
                continue
            title = cur.get("title") or ""
            if title and not title.lower().startswith(("about:", "chrome://")):
                time.sleep(0.6)
                try:
                    cur = next((x for x in _targets() if x.get("id") == tid), None) or cur
                except Exception:
                    pass
                title = cur.get("title") or title
                loaded = True
                break
        try:
            httpx.get(CDP + f"/json/activate/{tid}", timeout=5)
        except Exception:
            pass
        return {"opened": url, "in": "Chromium (Hoola PC)", "title": title, "loaded": loaded}

    def do_page_text(self, max_chars: int = 6000, **_) -> dict[str, Any]:
        _chrome_up()
        t = _active_target()
        n = max(500, min(int(max_chars or 6000), 20000))
        text = _cdp_eval(t, "document.body ? document.body.innerText : ''", timeout=20) or ""
        return {"title": t.get("title", ""), "url": t.get("url", ""), "text": str(text)[:n]}

    # ---- v1.3.0 SEMANTIC BROWSER (CDP): act on elements by ref, never by guessed pixels ----
    # The root cause of 'browser operations not smooth' was pixel clicking: a JPEG screenshot -> the model
    # guesses X,Y -> xdotool clicks. Every step was a vision round trip and a miss on layout shift / DPI.
    # Here the PAGE tells us its real elements (one cheap exact step) and the browser itself clicks/types
    # the element the model named - the click cannot miss, and page_fill_form does a whole form in ONE step.

    _JS_ELEMENTS = r"""
(() => {
  const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 1 && r.height > 1 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const nm = el => { let t = el.getAttribute('aria-label') || el.getAttribute('title') || el.placeholder || '';
    if (!t && el.value && ['INPUT','SELECT','TEXTAREA','BUTTON'].includes(el.tagName) && el.type !== 'password') t = String(el.value);
    if (!t && el.labels && el.labels[0]) t = el.labels[0].textContent;
    if (!t && el.tagName === 'IMG') t = el.alt || '';
    if (!t) t = (el.textContent || '').trim().replace(/\s+/g, ' ');
    return (t || '').trim().slice(0, 90); };
  const path = el => { if (el.id) return '#' + CSS.escape(el.id);
    const parts = []; let e = el;
    while (e && e.nodeType === 1 && parts.length < 7) {
      if (e.id) { parts.unshift('#' + CSS.escape(e.id)); break; }
      let s = e.tagName.toLowerCase(); const p = e.parentElement;
      if (p) { const sib = Array.from(p.children).filter(c => c.tagName === e.tagName);
        if (sib.length > 1) s += ':nth-of-type(' + (sib.indexOf(e) + 1) + ')'; }
      parts.unshift(s); e = p; }
    return parts.join(' > '); };
  const nodes = document.querySelectorAll('a[href], button, input, select, textarea, summary, [role="button"], [role="link"], [role="tab"], [role="checkbox"], [role="radio"], [role="combobox"], [role="menuitem"], [onclick]');
  const seen = new Set(); const out = [];
  for (const el of nodes) {
    if (out.length >= 300) break;
    if (!vis(el)) continue;
    const tag = el.tagName.toLowerCase(); const ty = (el.getAttribute('type') || '').toLowerCase();
    if (tag === 'input' && ['hidden','file'].includes(ty)) continue;
    const role = tag === 'input' ? ({checkbox:'checkbox', radio:'radio', button:'button', submit:'button', reset:'button'}[ty] || 'input')
                                 : (el.getAttribute('role') || (tag === 'a' ? 'link' : tag));
    const name = nm(el);
    const key = role + '|' + name + '|' + (el.disabled ? 'd' : 'e');
    if (seen.has(key) && !['input','textarea','select'].includes(role)) continue;
    seen.add(key);
    out.push({role, name, path: path(el), disabled: !!el.disabled,
              ph: (el.placeholder || '').slice(0, 60), ty: ty || undefined});
  }
  return {title: document.title, url: location.href, elements: out};
})()
"""

    def do_page_elements(self, max_items: int = 60, **_) -> dict[str, Any]:
        _chrome_up()
        t = _active_target()
        r = _cdp_eval(t, self._JS_ELEMENTS, timeout=25) or {}
        els = list(r.get("elements") or [])[:max(1, min(int(max_items or 60), 200))]
        out = []
        self._els = {}
        for i, e in enumerate(els, 1):
            self._els[i] = e.get("path") or ""
            item = {"ref": i, "role": e.get("role"), "name": e.get("name")}
            if e.get("ph"): item["placeholder"] = e["ph"]
            if e.get("ty"): item["type"] = e["ty"]
            if e.get("disabled"): item["disabled"] = True
            out.append(item)
        self._els_src = f"{r.get('title', '')}|{r.get('url', '')}"
        return {"title": r.get("title", ""), "url": r.get("url", ""), "count": len(out), "elements": out}

    def _ref_sel(self, ref: int) -> str:
        sel = self._els.get(int(ref or 0))
        if not sel:
            raise ActionError(f"ref {ref} gaya - pehle page_elements dobara chalao (page badla ya naya session)")
        return sel

    def _js_on_ref(self, sel: str, body: str) -> Any:
        """Run body(el) inside a IIFE after resolving sel; body returns a plain object."""
        t = _active_target()
        js = ("(() => { const el = document.querySelector(" + json.dumps(sel) + ");"
              " if (!el) return {ok:false, err:'gone'};" + body + "})()")
        return _cdp_eval(t, js, timeout=25) or {"ok": False, "err": "no-answer"}

    def do_page_click(self, ref: int, **_) -> dict[str, Any]:
        _chrome_up()
        sel = self._ref_sel(ref)
        r = self._js_on_ref(sel, """ el.scrollIntoView({block:'center'}); el.focus();
            const before = location.href; el.click();
            return {ok:true, was: before, now: location.href, title: document.title}; """)
        if not r.get("ok"):
            raise ActionError(f"click nahi hua ({r.get('err', '?')}) - page_elements dobara chalao")
        t = _active_target()
        return {"clicked": True, "title": t.get("title", ""), "url": t.get("url", ""),
                "navigated": r.get("was") != r.get("now")}

    _JS_TYPE = r""" el.scrollIntoView({block:'center'}); el.focus();
        if (el.disabled || el.readOnly) return {ok:false, err:'disabled'};
        if (CLR) { if (el.select) try { el.select(); } catch(e) {}
          let okDel = false; try { okDel = document.execCommand('delete'); } catch(e) {}
          if (!okDel && el.value !== undefined) { try { el.value = ''; } catch(e) {} } }
        let ok = false; try { ok = document.execCommand('insertText', false, TXT); } catch(e) {}
        if (!ok || (el.value || '') === '') {
          const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
          const d = Object.getOwnPropertyDescriptor(proto, 'value');
          if (d && d.set) { d.set.call(el, (el.value || '') + TXT);
            el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true})); }
        }
        const v = el.value || '';
        return {ok:true, length:v.length, matches: v === TXT || v.endsWith(TXT)};"""

    def do_page_type(self, ref: int, text: str = "", clear: bool = True, **_) -> dict[str, Any]:
        _chrome_up()
        sel = self._ref_sel(ref)
        txt = str(text or "")[:4000]
        js = ("(() => { const el = document.querySelector(" + json.dumps(sel) + ");"
              " if (!el) return {ok:false, err:'gone'};"
              " const TXT = " + json.dumps(txt) + "; const CLR = " + json.dumps(bool(clear)) + ";"
              + self._JS_TYPE + "})()")
        t = _active_target()
        r = _cdp_eval(t, js, timeout=25) or {"ok": False, "err": "no-answer"}
        if not r.get("ok"):
            raise ActionError(f"type nahi hua ({r.get('err', '?')}) - page_elements dobara chalao")
        return {"typed": True, "length": r.get("length"), "matches": r.get("matches"),
                "note": "value kabhi wapas nahi aati (sirf length + match)"}

    def do_page_select(self, ref: int, value: str = "", **_) -> dict[str, Any]:
        _chrome_up()
        sel = self._ref_sel(ref)
        js = ("(() => { const el = document.querySelector(" + json.dumps(sel) + ");"
              " if (!el) return {ok:false, err:'gone'};"
              " const VAL = " + json.dumps(str(value or "")) + ";"
              r""" if (el.tagName === 'SELECT') { el.focus();
                for (const o of el.options) { if (o.value === VAL || o.text.trim() === VAL ||
                    o.text.trim().toLowerCase() === VAL.toLowerCase()) { el.value = o.value;
                    el.dispatchEvent(new Event('input', {bubbles:true}));
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    return {ok:true, picked:o.text.trim()}; } }
                return {ok:false, err:'option', options: Array.from(el.options).slice(0,30).map(o=>o.text.trim())}; }
              el.focus();
              const d = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
              if (d && d.set) { d.set.call(el, VAL); el.dispatchEvent(new Event('input', {bubbles:true}));
                el.dispatchEvent(new Event('change', {bubbles:true})); }
              return {ok:true, picked:VAL}; })()""")
        t = _active_target()
        r = _cdp_eval(t, js, timeout=25) or {"ok": False, "err": "no-answer"}
        if not r.get("ok"):
            raise ActionError(f"select nahi hua ({r.get('err', '?')})"
                              + (f" - options: {', '.join((r.get('options') or [])[:12])}" if r.get("options") else ""))
        return {"selected": r.get("picked")}

    def do_page_fill_form(self, entries: list | dict | None = None, **_) -> dict[str, Any]:
        """Many fields in ONE step: entries = [{'ref': 2, 'text': '...'}, ...]. Each field types with the
        same execCommand + events path as page_type; results come back per entry (text never echoed)."""
        _chrome_up()
        items = entries.get("entries") if isinstance(entries, dict) else entries
        if not isinstance(items, list) or not items:
            raise ActionError("entries chahiye: [{'ref': 2, 'text': '...'}, ...]")
        out = []
        for it in items[:20]:
            try:
                ref = int(it.get("ref") or 0)
                sel = self._ref_sel(ref)
            except (ActionError, TypeError, ValueError) as e:
                out.append({"ref": it.get("ref"), "ok": False, "err": str(e)[:120]})
                continue
            txt = str(it.get("text") or "")[:4000]
            js = ("(() => { const el = document.querySelector(" + json.dumps(sel) + ");"
                  " if (!el) return {ok:false, err:'gone'};"
                  " const TXT = " + json.dumps(txt) + "; const CLR = true;" + self._JS_TYPE + "})()")
            try:
                r = _cdp_eval(_active_target(), js, timeout=25) or {"ok": False}
            except Exception as e:
                r = {"ok": False, "err": str(e)[:120]}
            out.append({"ref": ref, "ok": bool(r.get("ok")), "length": r.get("length"),
                        "matches": r.get("matches"), **({"err": r["err"]} if r.get("err") else {})})
        return {"filled": sum(1 for x in out if x.get("ok")), "total": len(out), "results": out}

    def do_wait_for(self, text: str = "", seconds: int = 15, **_) -> dict[str, Any]:
        """Wait until a text really appears on the page (polls innerText over CDP; max 20s)."""
        _chrome_up()
        want = str(text or "").strip()
        if not want:
            raise ActionError("Kis text ka intezaar?")
        end = time.time() + max(2, min(int(seconds or 15), 20))
        while time.time() < end:
            t = _active_target()
            body = str(_cdp_eval(t, "document.body ? document.body.innerText : ''", timeout=10) or "")
            if want.lower() in body.lower():
                return {"found": True, "title": t.get("title", "")}
            time.sleep(1.0)
        return {"found": False, "note": f"'{want[:60]}' {int(seconds or 15)}s mein nahi dikha"}

    def do_tabs(self, **_) -> dict[str, Any]:
        _chrome_up()
        ts = _targets()
        act = _active_window()
        tabs = [{"index": i + 1, "title": (t.get("title") or "")[:120],
                 "active": (t.get("title") == act) or (i == 0 and not act)} for i, t in enumerate(ts)]
        return {"tabs": tabs, "count": len(tabs)}

    def do_switch_tab(self, tab: str = "", index: int = 0, **_) -> dict[str, Any]:
        _chrome_up()
        ts = _targets()
        pick = None
        if index and 1 <= int(index) <= len(ts):
            pick = ts[int(index) - 1]
        else:
            q = str(tab or "").lower()
            pick = next((t for t in ts if q in (t.get("title") or "").lower()), None)
        if pick is None:
            raise ActionError("Waisa koi tab nahi khula")
        httpx.get(CDP + f"/json/activate/{pick['id']}", timeout=5)
        subprocess.run(["wmctrl", "-a", (pick.get("title") or "")[:80]], capture_output=True,
                       env={**os.environ, "DISPLAY": DISPLAY})
        return {"switched": (pick.get("title") or "")[:80], "title": pick.get("title", "")}

    def do_downloads(self, minutes: int = 15, **_) -> dict[str, Any]:
        mins = max(1, min(int(minutes or 15), 240))
        cutoff = time.time() - mins * 60
        files = []
        cand = sorted(DOWNLOADS.iterdir(), key=lambda c: c.stat().st_mtime if c.exists() else 0, reverse=True)[:20]
        for c in cand:
            if not c.is_file() or c.name.startswith("."):
                continue
            st = c.stat()
            if st.st_mtime < cutoff:
                break
            files.append({"name": c.name, "size_text": f"{st.st_size // 1024} KB", "partial": c.suffix == ".crdownload"})
        return {"files": files, "folder": str(DOWNLOADS)}

    # ---- files (same surface as Santosh Desktop, over /data) ----
    def do_status(self, **_) -> dict[str, Any]:
        i = self.info()
        i.pop("type", None)
        return i

    def do_list(self, path: str = "", **_) -> dict[str, Any]:
        p = Path(path or str(DATA))
        if not p.is_dir():
            raise ActionError("Yeh folder nahi hai")
        entries = []
        for c in sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower()))[:300]:
            if c.name.startswith("."):
                continue
            try:
                st = c.stat()
            except OSError:
                continue
            entries.append({"name": c.name, "path": str(c), "dir": c.is_dir(), "size": st.st_size if c.is_file() else None,
                            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))})
        return {"path": str(p), "entries": entries}

    def do_read(self, path: str = "", max_chars: int = 12000, **_) -> dict[str, Any]:
        p = Path(path)
        if not p.is_file():
            raise ActionError("File nahi mili")
        n = max(500, min(int(max_chars or 12000), 40000))
        try:
            text = p.read_text(errors="ignore")[:n]
        except Exception as e:
            raise ActionError(f"Padh nahi paya: {e}")
        return {"path": str(p), "name": p.name, "text": text}

    def do_save_file(self, file_id: str = "", name: str = "", url: str = "", **_) -> dict[str, Any]:
        stem = Path(name or file_id or "file").stem
        ext = Path(name or file_id or "file").suffix
        dest = DOWNLOADS / (stem + ext)
        n = 1
        while dest.exists():                     # v0.202 never overwrite (Windows desktop parity)
            dest = DOWNLOADS / f"{stem} ({n}){ext}"
            n += 1
        with httpx.stream("GET", SERVER + (url or f"/api/pc/fetch/{file_id}"), timeout=300) as r:
            if r.status_code >= 400:
                raise ActionError(f"Download failed ({r.status_code})")
            with dest.open("wb") as out:
                for chunk in r.iter_bytes():
                    out.write(chunk)
        return {"saved_path": str(dest), "name": dest.name,
                "message": f"{dest.name} Hoola PC ke Downloads mein save ho gayi."}

    def do_send_file(self, path: str = "", **_) -> dict[str, Any]:
        """v0.202 the PC-to-PC bridge: hand one of MY files to the server so the USER'S personal PC can
        fetch it (her desktop saves it into her Santosh Inbox after she approves the confirm card the
        operator raised). Tagged direction "to_pc": only her paired desktop can fetch it - a phone
        download link can never pick it up. Same shape as the Windows desktop's do_send_file."""
        p = Path(path)
        if not p.is_absolute():
            p = DATA / p
        if not p.is_file():
            raise ActionError("File nahi mili")
        size = p.stat().st_size
        if size > MAX_SEND:
            raise ActionError(f"{p.name} is {size // (1024 * 1024)} MB; the limit is 50 MB.")
        token = _identity().get("token", "")
        with p.open("rb") as fh:
            r = httpx.post(SERVER + "/api/pc/files", headers={"Authorization": f"Bearer {token}"},
                           files={"file": (p.name, fh, "application/octet-stream")},
                           data={"path": str(p), "direction": "to_pc"}, timeout=300)
        if r.status_code >= 400:
            raise ActionError(f"Upload failed ({r.status_code}): {r.text[:160]}")
        return r.json()

    # ---- THE COWORKER SURFACE: install software + run commands (Hoola's own VM) ----
    def do_install(self, packages: str = "", pip: bool = False, **_) -> dict[str, Any]:
        pkgs = str(packages or "").strip()
        if not pkgs:
            raise ActionError("Batayiye kya install karna hai")
        if any(ch in pkgs for ch in ";|&`$>\n"):
            raise ActionError("Ek baar mein sirf package naam (koi shell nahi). Alag-alag naam dijiye.")
        names = pkgs.split()
        if pip:
            cmd = ["pip", "install", "--quiet", "--no-input", *names]
        else:
            subprocess.run(["apt-get", "update", "-qq"], capture_output=True, timeout=240)
            cmd = ["apt-get", "install", "-y", *names]
        env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=480, env=env)
        except subprocess.TimeoutExpired:
            raise ActionError("Install ne 8 minute mein jawab nahi diya (network dheema hai). Dobara koshish kijiye.")
        tail = ((p.stdout or "") + (p.stderr or ""))[-1500:]
        line = f"{time.strftime('%m-%d %H:%M')} {'pip' if pip else 'apt'} {pkgs} rc={p.returncode}"
        with (DATA / "installed.log").open("a") as fh:
            fh.write(line + "\n")
        if p.returncode != 0:
            raise ActionError(f"Install fail (rc={p.returncode}): {tail[-400:]}")
        return {"installed": names, "pip": bool(pip), "note": tail[-400:] or "installed"}

    def do_run(self, command: str = "", timeout: int = 60, **_) -> dict[str, Any]:
        cmd = str(command or "").strip()
        if not cmd:
            raise ActionError("Kaunsa command?")
        limit = max(5, min(int(timeout or 60), 180))
        try:
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=limit,
                               env={**os.environ, "DISPLAY": DISPLAY, "HOME": str(DATA)}, cwd=str(DATA))
        except subprocess.TimeoutExpired:
            raise ActionError(f"Command {limit}s mein ruk gaya (timeout).")
        return {"exit": p.returncode, "stdout": (p.stdout or "")[-6000:],
                "stderr": (p.stderr or "")[-1500:], "cwd": str(DATA)}


# ---------------- the bridge (same protocol as the Windows desktop) ----------------
def _ws_url(server: str) -> str:
    s = server.rstrip("/")
    scheme = "ws://" if not s.startswith("https://") else "wss://"
    return scheme + s.split("://", 1)[1] + "/api/pc/ws"


async def _connect(url: str, token: str):
    import websockets
    headers = {"Authorization": f"Bearer {token}"}
    try:
        from websockets.asyncio.client import connect  # websockets >= 13
        return await connect(url, additional_headers=headers, max_size=8 * 1024 * 1024, ping_interval=30, open_timeout=20)
    except ImportError:
        return await websockets.connect(url, extra_headers=headers, max_size=8 * 1024 * 1024, ping_interval=30)


class Bridge:
    def __init__(self, actions: Actions) -> None:
        self.actions = actions
        self.ws: Any = None

    async def _send(self, msg: dict[str, Any]) -> None:
        if self.ws is not None:
            await self.ws.send(json.dumps(msg, ensure_ascii=False, default=str))

    async def run_forever(self) -> None:
        delay = 1.0
        while True:
            if not _identity():
                code_file = DATA / "pair_code"
                code = code_file.read_text().strip() if code_file.exists() else ""
                if len(code) == 6 and code.isdigit():
                    try:
                        device_id = await asyncio.to_thread(pair_once, code)
                        code_file.unlink()
                        print(f"PAIRED: {device_id}", flush=True)
                    except Exception as e:
                        print(f"pair failed: {e}", flush=True)
                        await asyncio.sleep(5)
                    continue
                print("waiting for pair code: docker exec hoola-pc sh -c 'echo 123456 > /data/pair_code'", flush=True)
                await asyncio.sleep(3)
                continue
            ident = _identity()
            try:
                self.ws = await _connect(_ws_url(SERVER), ident["token"])
                print("connected: Hoola PC is online", flush=True)
                delay = 1.0
                await self._send(self.actions.info())
                async for raw in self.ws:
                    try:
                        msg = json.loads(raw)
                    except ValueError:
                        continue
                    t = msg.get("type")
                    if t == "hello":
                        await self._send(self.actions.info())
                    elif t == "ping":
                        await self._send({"type": "pong"})
                    elif t == "job":
                        asyncio.create_task(self._job(msg))
            except Exception as e:
                code = getattr(getattr(e, "rcvd", None), "code", None) or getattr(e, "code", None)
                if code in (4401, 4403):
                    print("unpaired by the server; waiting for a new pair code", flush=True)
                    (DATA / "identity.json").unlink(missing_ok=True)
                    continue
                print(f"connection toota, {int(delay)}s mein dobara… ({type(e).__name__})", flush=True)
            finally:
                self.ws = None
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)

    async def _job(self, msg: dict[str, Any]) -> None:
        jid, action, args = msg.get("id"), str(msg.get("action") or ""), msg.get("args") or {}
        t0 = time.time()
        try:
            data = await asyncio.to_thread(self.actions.handle, action, args)
            reply = {"type": "result", "id": jid, "ok": True, "data": data}
        except ActionError as e:
            reply = {"type": "result", "id": jid, "ok": False, "error": str(e)[:300]}
        except Exception as e:
            reply = {"type": "result", "id": jid, "ok": False, "error": f"{type(e).__name__}: {e}"[:300]}
        print(f"job {action} -> {'ok' if reply.get('ok') else str(reply.get('error', ''))[:80]} ({time.time() - t0:.1f}s)", flush=True)
        try:
            await self._send(reply)
        except Exception:
            pass


def main() -> None:
    print(f"Hoola PC agent {VERSION} -> {SERVER} (display {DISPLAY})", flush=True)
    asyncio.run(Bridge(Actions()).run_forever())


if __name__ == "__main__":
    main()

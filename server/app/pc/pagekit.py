"""v0.999.93 ULTIMATE PC PLAN P1 - Hoola PC's page engine 2 (docs/HOOLA_ULTIMATE_PC_PLAN.md).

What the first browser exam (v0.999.84, 24 / 30) showed and this file fixes:
- a page element was found only in the top page: a form inside a WEB COMPONENT (shadow DOM) or a frame was invisible;
- a ref was a position on the page (li:nth-of-type(3) > button): after the page re-drew itself the same ref quietly
  pointed at ANOTHER element. Now every ref also carries what it was (role + name) and is checked before it is used;
  an element that moved is found again by what it is, an element that is gone is said to be gone;
- a click was el.click(): it never moved the mouse (hover menus never opened) and clicked straight through a cookie
  banner lying on top. Now a click is an HONEST click - the real mouse goes to the element's centre (CDP
  Input.dispatchMouseEvent), and if something else is lying on top the click is not made and the answer names it;
- a date box was typed into like text (it takes only yyyy-mm-dd); now the date is understood and set;
- after an action the model never knew what changed (a menu that opened, a message that appeared): every action now
  returns the page diff (elements that appeared / went away, new lines of text).

Ideas from vercel-labs/agent-browser + microsoft/playwright-mcp (Apache-2.0: refs from a snapshot, actionability /
hit-target checks, the snapshot diff); the code here is Hoola's own. Credit in THIRD_PARTY_NOTICES.md."""
from __future__ import annotations

import re
from datetime import date

# Shared JS: walk every reachable document (the page, OPEN shadow roots, same-origin frames) in order.
# A path is a list of hops: {k:'f'|'s'|'e', sel}; 'f' = an <iframe> to enter, 's' = a shadow host to enter, 'e' = the element.
JS_PRE = r"""
const _vis = el => { const r = el.getBoundingClientRect(); const s = el.ownerDocument.defaultView.getComputedStyle(el);
  return r.width > 1 && r.height > 1 && s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0'; };
const _txt = el => (el.textContent || '').trim().replace(/\s+/g, ' ');
const _nm = el => { let t = el.getAttribute('aria-label') || el.getAttribute('title') || el.placeholder || '';
  if (!t && el.getAttribute('aria-labelledby')) { const l = el.getRootNode().getElementById &&
      el.getRootNode().getElementById(el.getAttribute('aria-labelledby')); if (l) t = _txt(l); }
  if (!t && el.labels && el.labels[0]) t = _txt(el.labels[0]);
  // what was TYPED into a box never names it (the value must not travel back to the model); a button's value is its label
  const btn = el.tagName === 'BUTTON' || (el.tagName === 'INPUT' && ['button','submit','reset'].includes((el.type || '').toLowerCase()));
  if (!t && btn && el.value) t = String(el.value);
  if (!t && el.tagName === 'SELECT' && el.selectedOptions && el.selectedOptions[0]) t = 'choice: ' + _txt(el.selectedOptions[0]);
  if (!t && ['INPUT','TEXTAREA','SELECT'].includes(el.tagName)) return (el.name ? el.name : (el.type || el.tagName.toLowerCase()) + ' box').slice(0, 90);
  if (!t && el.isContentEditable) return 'text editor';
  if (!t && el.tagName === 'IMG') t = el.alt || '';
  if (!t) t = _txt(el);
  t = (t || '').trim();
  if (t.length <= 2 && !/[A-Za-z0-9]/.test(t)) {            // a bare arrow / x / + : say which row it belongs to
    const row = el.closest('li,tr,[role=row],[role=listitem],.card'); const rt = row ? _txt(row).replace(t, '').trim() : '';
    if (rt) t = (t + ' (' + rt.slice(0, 40) + ')').trim(); }
  return t.slice(0, 90); };
const _sel = (el, root) => { if (el.id && root.querySelectorAll('#' + CSS.escape(el.id)).length === 1) return '#' + CSS.escape(el.id);
  const parts = []; let e = el;
  while (e && e.nodeType === 1 && parts.length < 9) {
    if (e.id && root.querySelectorAll('#' + CSS.escape(e.id)).length === 1) { parts.unshift('#' + CSS.escape(e.id)); break; }
    let s = e.tagName.toLowerCase(); const p = e.parentElement;
    if (p) { const sib = Array.from(p.children).filter(c => c.tagName === e.tagName);
      if (sib.length > 1) s += ':nth-of-type(' + (sib.indexOf(e) + 1) + ')'; }
    else if (e.parentNode && e.parentNode !== root && e.parentNode.nodeType !== 11) { }
    parts.unshift(s); e = p; }
  return parts.join(' > '); };
const _role = el => { const tag = el.tagName.toLowerCase(); const ty = (el.getAttribute('type') || '').toLowerCase();
  if (tag === 'input') return ({checkbox:'checkbox', radio:'radio', button:'button', submit:'button', reset:'button',
                                date:'date', 'datetime-local':'date', month:'date', time:'time'}[ty] || 'input');
  if (el.isContentEditable && !el.parentElement?.isContentEditable) return 'textbox';
  return el.getAttribute('role') || (tag === 'a' ? 'link' : tag); };
const _Q = 'a[href], button, input, select, textarea, summary, [role="button"], [role="link"], [role="tab"], [role="checkbox"], [role="radio"], [role="combobox"], [role="menuitem"], [role="option"], [role="switch"], [role="textbox"], [contenteditable="true"], [onclick], [draggable="true"]';
function _walk(visit) {              // visit(el, hops, root) for every element of every reachable document
  let blocked = 0;
  const go = (root, hops, depth) => {
    if (depth > 6) return;
    const all = root.querySelectorAll('*');
    for (const el of all) {
      visit(el, hops, root);
      if (el.shadowRoot) go(el.shadowRoot, hops.concat([{k:'s', sel:_sel(el, root)}]), depth + 1);
      if (el.tagName === 'IFRAME' || el.tagName === 'FRAME') {
        let d = null; try { d = el.contentDocument; } catch (e) {}
        if (d && d.documentElement) go(d, hops.concat([{k:'f', sel:_sel(el, root)}]), depth + 1); else blocked++;
      }
    }
  };
  go(document, [], 0);
  return blocked;
}
function _resolve(path) {           // path -> [el, offsetX, offsetY] (offsets = where its document sits in the top page)
  let root = document, ox = 0, oy = 0;
  for (const h of path) {
    const el = root.querySelector(h.sel);
    if (!el) return [null, 0, 0];
    if (h.k === 'e') return [el, ox, oy];
    if (h.k === 's') { root = el.shadowRoot; if (!root) return [null, 0, 0]; }
    if (h.k === 'f') { const r = el.getBoundingClientRect(); ox += r.left + el.clientLeft; oy += r.top + el.clientTop;
      try { root = el.contentDocument; } catch (e) { return [null, 0, 0]; } if (!root) return [null, 0, 0]; }
  }
  return [null, 0, 0];
}
function _find(path, role, name) {   // the element the ref meant: at its place if it is still the same, else by what it is
  const [el, ox, oy] = _resolve(path);
  // a ref is used only while its element is still ON the page: a wizard's next step hides the last step's boxes, and
  // typing into the hidden 'Full name' was how the street address landed in the name (exam v2, wizard_account)
  if (el && _vis(el) && (!name || _nm(el) === name) && (!role || _role(el) === role)) return {el, ox, oy, moved:false};
  let hit = null;
  if (name) _walk((e, hops) => { if (!hit && e.matches && e.matches(_Q) && _vis(e) && _role(e) === role && _nm(e) === name)
    hit = hops.concat([{k:'e', sel:_sel(e, e.getRootNode())}]); });
  if (hit) { const [e2, x2, y2] = _resolve(hit); if (e2) return {el:e2, ox:x2, oy:y2, moved:true, path:hit}; }
  return null;
}
function _hit(x, y) {               // the real element under a top-page point, through frames and shadow roots
  let root = document, px = x, py = y;
  for (let i = 0; i < 10; i++) {
    let e = root.elementFromPoint(px, py); if (!e) return null;
    for (let j = 0; j < 8 && e.shadowRoot; j++) { const inner = e.shadowRoot.elementFromPoint(px, py);
      if (!inner || inner === e) break; e = inner; }
    if (e.tagName === 'IFRAME' || e.tagName === 'FRAME') { let d = null; try { d = e.contentDocument; } catch (e2) {}
      if (!d) return e; const r = e.getBoundingClientRect(); px -= r.left + e.clientLeft; py -= r.top + e.clientTop; root = d; continue; }
    return e;
  }
  return null;
}
function _within(h, el) {          // h inside el, across shadow roots
  for (let n = h, i = 0; n && i < 60; i++) { if (n === el) return true;
    n = n.parentNode || (n.host || null); if (n && n.nodeType === 11) n = n.host; }
  return false;
}
function _snap() {                  // a light picture of the page, for the before / after diff
  const keys = []; const lines = new Set();
  _walk((el) => { if (keys.length < 400 && el.matches && el.matches(_Q) && _vis(el)) keys.push(_role(el) + ': ' + _nm(el)); });
  const add = d => { const t = (d.body ? d.body.innerText : '') || '';
    const typed = new Set();          // what she / Hoola typed into an editor is not page news (and never travels back)
    for (const ed of d.querySelectorAll('[contenteditable=""],[contenteditable="true"]'))
      for (const l of (ed.innerText || '').split('\n')) if (l.trim()) typed.add(l.trim());
    for (const l of t.split('\n')) { const s = l.trim();
      if (s && !typed.has(s) && s.length < 160 && lines.size < 600) lines.add(s); } };
  add(document);
  _walk((el) => { if (el.shadowRoot) { for (const n of el.shadowRoot.querySelectorAll('*')) { const s = (n.childElementCount ? '' : _txt(n));
        if (s && s.length < 160 && lines.size < 600) lines.add(s); } }
    if (el.tagName === 'IFRAME') { try { if (el.contentDocument) add(el.contentDocument); } catch (e) {} } });
  return {url: location.href, title: document.title, keys, lines: Array.from(lines)};
}
"""

JS_ELEMENTS = "(() => {" + JS_PRE + r"""
  const seen = new Set(); const out = []; let shadow = 0, frames = 0;
  const blocked = _walk((el, hops, root) => {
    if (out.length >= 300 || !(el.matches && el.matches(_Q)) || !_vis(el)) return;
    const tag = el.tagName.toLowerCase(); const ty = (el.getAttribute('type') || '').toLowerCase();
    if (tag === 'input' && ['hidden','file'].includes(ty)) return;
    const role = _role(el); const name = _nm(el);
    const key = role + '|' + name + '|' + (el.disabled ? 'd' : 'e') + '|' + hops.length;
    if (seen.has(key) && !['input','textarea','select','date','time','textbox'].includes(role)) return;
    seen.add(key);
    if (hops.some(h => h.k === 's')) shadow++;
    if (hops.some(h => h.k === 'f')) frames++;
    const where = hops.some(h => h.k === 'f') ? 'frame' : (hops.some(h => h.k === 's') ? 'component' : '');
    out.push({role, name, path: hops.concat([{k:'e', sel:_sel(el, root)}]), disabled: !!el.disabled,
              ph: (el.placeholder || '').slice(0, 60), ty: ty || undefined, where: where || undefined,
              drag: el.getAttribute('draggable') === 'true' || undefined});
  });
  return {title: document.title, url: location.href, elements: out, in_shadow: shadow, in_frames: frames, blocked_frames: blocked};
})()"""

JS_SNAP = "(() => {" + JS_PRE + "return _snap(); })()"

# v0.999.114 P3 page data into rows: every table of the page (and of its components / same-site frames) as plain rows
JS_TABLES = "(() => {" + JS_PRE + r"""
  const out = [];
  const grab = (t, where) => {
    if (out.length >= 20 || !_vis(t)) return;
    const rows = [];
    for (const tr of t.querySelectorAll('tr')) {
      if (rows.length >= 300) break;
      const cells = Array.from(tr.children).filter(c => /^(TD|TH)$/.test(c.tagName)).slice(0, 30)
        .map(c => (c.innerText || c.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 200));
      if (cells.length) rows.push(cells);
    }
    if (rows.length) out.push({caption: (t.caption ? _txt(t.caption) : (t.getAttribute('aria-label') || '')).slice(0, 120),
                              where: where, rows: rows});
  };
  _walk((el, hops) => { if (el.tagName === 'TABLE')
    grab(el, hops.some(h => h.k === 'f') ? 'frame' : (hops.some(h => h.k === 's') ? 'component' : '')); });
  return {title: document.title, url: location.href, tables: out};
})()"""

# the page's text in reading order, plus the text inside web components and same-origin frames (labelled)
JS_TEXT = "(() => {" + JS_PRE + r"""
  let out = document.body ? document.body.innerText : '';
  const extra = [];
  _walk((el) => {
    if (el.shadowRoot) { const t = Array.from(el.shadowRoot.querySelectorAll('*')).filter(n => !n.childElementCount)
        .map(n => n.tagName === 'INPUT' ? '' : _txt(n)).filter(Boolean).join('\n');
      if (t) extra.push('[inside a page component]\n' + t); }
    if (el.tagName === 'IFRAME' || el.tagName === 'FRAME') { try { const d = el.contentDocument;
        if (d && d.body && d.body.innerText.trim()) extra.push('[inside a frame]\n' + d.body.innerText); } catch (e) {} }
  });
  return out + (extra.length ? '\n\n' + extra.join('\n\n') : '');
})()"""


def js_on(path: list, role: str, name: str, body: str) -> str:
    """JS that finds the ref's element (checked by what it is) and runs body with el / ox / oy / moved in scope."""
    import json
    return ("(() => {" + JS_PRE + "const P = " + json.dumps(path) + "; const F = _find(P, " + json.dumps(role or "")
            + ", " + json.dumps(name or "") + "); if (!F) return {ok:false, err:'gone'};"
            " const el = F.el, ox = F.ox, oy = F.oy, moved = F.moved, newpath = F.path || null;" + body + "})()")


# where to aim the honest click: scroll into view, the centre in TOP-page coordinates, and what really lies there
POINT_BODY = r"""
  el.scrollIntoView({block:'center', inline:'center'});
  const r = el.getBoundingClientRect();
  if (r.width < 1 || r.height < 1) return {ok:true, x:null, y:null, moved, newpath, why:'no size'};
  const x = Math.round(ox + r.left + r.width / 2), y = Math.round(oy + r.top + r.height / 2);
  const h = _hit(x, y);
  const mine = h && _within(h, el);
  let cover = '';
  if (h && !mine) { let c = h; for (let i = 0; i < 6 && c.parentElement; i++) { const s = getComputedStyle(c);
      if (s.position === 'fixed' || s.position === 'sticky' || s.position === 'absolute') break; c = c.parentElement; }
    cover = (_txt(c) || _nm(h)).slice(0, 120); }
  return {ok:true, x, y, covered: !mine && !!h, cover, tag: el.tagName.toLowerCase(), moved, newpath,
          disabled: !!el.disabled};
"""

CLICK_FALLBACK = "el.click(); return {ok:true};"

# v1.9.2 typing + choosing, shared by Hoola PC (agent.py) and her Chrome (the Hoola extension). Uses TXT / CLR / ISO
# (typing) and VAL (choosing), set by the caller. A password box is refused here; the value itself never comes back.
TYPE_BODY = r""" if ((el.type || '').toLowerCase() === 'password' || /password/i.test(el.getAttribute('autocomplete') || ''))
          return {ok:false, err:'password'};    // v1.9.1 Hoola never types a password: ask_login (she types it privately)
        el.scrollIntoView({block:'center'}); el.focus();
        if (el.disabled || el.readOnly) return {ok:false, err:'disabled'};
        if (ISO) { const d = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
          d.set.call(el, ISO); el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true}));
          return {ok:true, length:(el.value || '').length, matches: el.value === ISO, as_date: true}; }
        if (el.isContentEditable && el.value === undefined) {
          if (CLR) { const s = el.ownerDocument.defaultView.getSelection(); const rg = el.ownerDocument.createRange();
            rg.selectNodeContents(el); s.removeAllRanges(); s.addRange(rg); }
          try { el.ownerDocument.execCommand('insertText', false, TXT); } catch(e) {}
          const v = el.innerText || '';
          return {ok:true, length:v.length, matches: v.trim() === TXT.trim() || v.includes(TXT)}; }
        if (CLR) { if (el.select) try { el.select(); } catch(e) {}
          let okDel = false; try { okDel = el.ownerDocument.execCommand('delete'); } catch(e) {}
          if (!okDel && el.value !== undefined) { try { el.value = ''; } catch(e) {} } }
        let ok = false; try { ok = el.ownerDocument.execCommand('insertText', false, TXT); } catch(e) {}
        if (!ok || (el.value || '') === '') {
          const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
          const d = Object.getOwnPropertyDescriptor(proto, 'value');
          if (d && d.set) { d.set.call(el, (CLR ? '' : (el.value || '')) + TXT);
            el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true})); }
        }
        const v = el.value || '';
        return {ok:true, length:v.length, matches: v === TXT || v.endsWith(TXT)};"""

SELECT_BODY = r"""
              if (el.tagName === 'SELECT') { el.focus();
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
              return {ok:true, picked:VAL};"""

DRAG_BODY = r"""
  const D = T.el;
  if (!D) return {ok:false, err:'target gone'};
  el.scrollIntoView({block:'center'});
  const dt = new DataTransfer();
  const ev = (n, t) => t.dispatchEvent(new DragEvent(n, {bubbles:true, cancelable:true, dataTransfer:dt}));
  ev('dragstart', el); ev('dragenter', D); ev('dragover', D); ev('drop', D); ev('dragend', el);
  return {ok:true};
"""

DATE_TYPES = ("date", "datetime-local", "month", "time")

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def iso_date(text: str, day_first: bool = True) -> str:
    """'12 April 1988' / 'April 12, 1988' / '12/04/1988' / '1988-04-12' -> '1988-04-12'; '' when it is not a date.
    Numbers like 03/04/2026 are read day first unless the user's country writes month first (the US)."""
    t = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", str(text or "").strip().lower()).replace(",", " ")
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", t)
    if m:
        y, mo, d = map(int, m.groups())
    else:
        m = re.fullmatch(r"(\d{1,2})\s+([a-z]{3,9})\.?\s+(\d{4})", t)
        m2 = re.fullmatch(r"([a-z]{3,9})\.?\s+(\d{1,2})\s+(\d{4})", t)
        m3 = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", t)
        if m and m.group(2)[:3] in _MONTHS:
            d, mo, y = int(m.group(1)), _MONTHS[m.group(2)[:3]], int(m.group(3))
        elif m2 and m2.group(1)[:3] in _MONTHS:
            mo, d, y = _MONTHS[m2.group(1)[:3]], int(m2.group(2)), int(m2.group(3))
        elif m3:
            a, b, y = int(m3.group(1)), int(m3.group(2)), int(m3.group(3))
            d, mo = (a, b) if day_first else (b, a)
            if mo > 12 and d <= 12:
                d, mo = mo, d                  # 25/12 written either way: only one reading is a real date
        else:
            return ""
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return ""


def field_value(text: str, ftype: str, day_first: bool = True) -> str:
    """The exact value a date / month / time box takes, or '' (then the text is typed as it is)."""
    ft = str(ftype or "").lower()
    if ft == "date":
        return iso_date(text, day_first)
    if ft == "month":
        d = iso_date(text, day_first) or iso_date("1 " + str(text), day_first)
        return d[:7] if d else ""
    if ft == "time":
        m = re.fullmatch(r"\s*(\d{1,2})[:.](\d{2})\s*(am|pm)?\s*", str(text or "").lower())
        if not m:
            return ""
        h, mi = int(m.group(1)), int(m.group(2))
        if m.group(3) == "pm" and h < 12:
            h += 12
        if m.group(3) == "am" and h == 12:
            h = 0
        return f"{h:02d}:{mi:02d}" if h < 24 and mi < 60 else ""
    if ft == "datetime-local":
        parts = str(text or "").rsplit(" ", 1)
        if len(parts) == 2:
            d, tm = iso_date(parts[0], day_first), field_value(parts[1], "time")
            return f"{d}T{tm}" if d and tm else ""
    return ""


def diff(before: dict | None, after: dict | None, limit: int = 8) -> dict:
    """What an action changed on the page: elements that appeared / went away, new text lines, a new address."""
    if not before or not after:
        return {}
    bk, ak = before.get("keys") or [], after.get("keys") or []
    bl = set(before.get("lines") or [])
    bset, aset = set(bk), set(ak)
    out: dict = {}
    if before.get("url") != after.get("url"):
        out["url"] = after.get("url")
    new_els = [k for k in ak if k not in bset]
    gone = [k for k in bk if k not in aset]
    new_txt = [ln for ln in (after.get("lines") or []) if ln not in bl]
    if new_els:
        out["appeared"] = new_els[:limit]
    if gone:
        out["gone"] = gone[:limit]
    if new_txt:
        out["new_text"] = new_txt[:5]
    if not out and bk != ak and bset == aset:
        out["reordered"] = True
    if not out:
        out["nothing"] = True
    return out


def diff_line(d: dict) -> str:
    """One line for the model (the page's words are DATA, said as such)."""
    if not d:
        return ""
    if d.get("nothing"):
        return "page change: NOTHING visible changed"
    parts = []
    if d.get("url"):
        parts.append(f"now at {str(d['url'])[:120]}")
    if d.get("appeared"):
        parts.append("appeared: " + "; ".join(str(x)[:60] for x in d["appeared"]))
    if d.get("gone"):
        parts.append("gone: " + "; ".join(str(x)[:60] for x in d["gone"][:5]))
    if d.get("reordered"):
        parts.append("the same items are now in a different order")
    if d.get("new_text"):
        parts.append("new text (page data): " + " | ".join(str(x)[:80] for x in d["new_text"]))
    return "page change: " + " / ".join(parts)


# ---------------------------------------------------------------- v1.9.2 the same engine inside her Chrome
def _body(js: str) -> str:
    """The statements of one of the IIFEs above, without the shared helpers and the call wrapper."""
    head = "(() => {" + JS_PRE
    assert js.startswith(head) and js.rstrip().endswith("})()")
    return js[len(head):].rstrip()[:-4]


def extension_js() -> str:
    """desktop/ext/hoola-extension/pagekit.js - GENERATED from this file (a test keeps them equal). The Hoola extension
    injects it into the page (its own isolated world: the page's scripts cannot touch it) and calls window.__hoolaPK.<fn>;
    the server keeps the refs and decides (pc/extlink.py), exactly as agent.py does on Hoola PC."""
    w = "(el, ox, oy, moved, newpath) => {"
    return ("// GENERATED by desktop-linux/pagekit.py extension_js() - do not edit by hand (v0.999.111 ULTIMATE PC PLAN P1).\n"
            "// Hoola's page engine 2 inside her Chrome: frames, page components, refs checked by what they are, the\n"
            "// honest-click aim, typing (never a password), choosing, drag, the page diff. Returns data only.\n"
            "(() => {\nif (window.__hoolaPK) return;\n" + JS_PRE +
            "\nconst _with = (a, fn) => { const F = _find(a.path || [], a.role || '', a.name || '');"
            " if (!F) return {ok:false, err:'gone'}; return fn(F.el, F.ox, F.oy, F.moved, F.path || null); };\n"
            "window.__hoolaPK = {\n"
            "  elements: () => {" + _body(JS_ELEMENTS) + "},\n"
            "  snap: () => _snap(),\n"
            "  text: () => {" + _body(JS_TEXT) + "},\n"
            "  tables: () => {" + _body(JS_TABLES) + "},\n"
            "  point: (a) => _with(a, " + w + POINT_BODY + "}),\n"
            "  click: (a) => _with(a, " + w + CLICK_FALLBACK + "}),\n"
            "  type: (a) => _with(a, " + w + " const TXT = String(a.txt || ''), CLR = !!a.clr, ISO = String(a.iso || '');"
            + TYPE_BODY + "}),\n"
            "  select: (a) => _with(a, " + w + " const VAL = String(a.val || '');" + SELECT_BODY + "}),\n"
            "  drag: (a) => { const F = _find(a.src.path, a.src.role, a.src.name);"
            " const T = _find(a.dst.path, a.dst.role, a.dst.name) || {}; if (!F) return {ok:false, err:'gone'};"
            " const el = F.el;" + DRAG_BODY + "},\n"
            "};\n})();\n")


if __name__ == "__main__":       # python desktop-linux/pagekit.py > desktop/ext/hoola-extension/pagekit.js
    import sys as _s
    _s.stdout.write(extension_js())

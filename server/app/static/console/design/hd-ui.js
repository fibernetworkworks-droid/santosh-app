/* HOOLA DESIGN - the editor's interface (docs/HOOLA_DESIGN_PLAN.md, section 3: HD.ui).
   The shell around the canvas: top bar, pages + layers on the left, the Design panel on the right, menus, the colour
   picker, the command palette and the keyboard. Nothing here draws a layer: the canvas belongs to HD.render, the
   pointer to HD.tools. Every edit is one HD.store transaction; every text from the document is set with textContent
   (never as HTML). Later phases plug in through registerPanel / registerMenu / registerShortcut / hook. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const NS = 'http://www.w3.org/2000/svg';
  const MIXED = {mixed: true};
  const T = () => HD.tools, U = () => HD.tools.u, A = () => HD.tools.act;
  const MAC = /Mac|iPhone|iPad/.test(navigator.platform || '');

  /* ---------------------------------------------------------------- DOM */
  function add(el, kid) { if (kid === null || kid === undefined || kid === false) return; if (Array.isArray(kid)) { for (const k of kid) add(el, k); return; }
    el.appendChild(typeof kid === 'string' || typeof kid === 'number' ? document.createTextNode(String(kid)) : kid); }
  function h(tag, a) {
    const el = document.createElement(tag);
    if (a) for (const k in a) { const v = a[k]; if (v === null || v === undefined || v === false) continue;
      if (k === 'class') el.className = v; else if (k === 'text') el.textContent = v; else if (k === 'on') { for (const ev in v) el.addEventListener(ev, v[ev]); }
      else if (k === 'style') Object.assign(el.style, v); else if (k === 'value' || k === 'checked' || k === 'disabled' || k === 'hidden' || k === 'tabIndex') el[k] = v;
      else el.setAttribute(k, v === true ? '' : String(v)); }
    for (let i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
  function esc(v) { return (v === null || v === undefined ? '' : String(v)).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c])); }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function fmt(v, dec) { const k = Math.pow(10, dec === undefined ? 2 : dec), r = Math.round(v * k) / k; return String(r === 0 ? 0 : r); }

  /* ---------------------------------------------------------------- icons (own drawings, 16 x 16, built as DOM) */
  const I = {
    move: ['M3.2 2.4l9.6 4.3-3.9 1.5-1.5 4z'], frame: ['M2.5 5.8V2.5h3.3M10.2 2.5h3.3v3.3M13.5 10.2v3.3h-3.3M5.8 13.5H2.5v-3.3', ['r', 5.6, 5.6, 4.8, 4.8, .8]],
    rect: [['r', 2.8, 3.3, 10.4, 9.4, 1.6]], ellipse: [['c', 8, 8, 5.4]], line: ['M3 13L13 3'], polygon: ['M8 2.6l5.9 10.2H2.1z'],
    star: ['M8 1.9l1.8 3.9 4.2.5-3.1 2.9.8 4.2L8 11.3l-3.7 2.1.8-4.2L2 6.3l4.2-.5z'],
    pen: ['M2.6 13.4l1.2-4.3L10 2.9l3.1 3.1-6.2 6.2z', 'M8.5 4.4l3.1 3.1'], pencil: ['M2 11.5c1.5-5 3.2-6 4-2.5.6 2.6 2 2.6 3.2-.8C10.3 5 12 4.5 14 7'],
    text: ['M3.5 4.4V3h9v1.4M8 3v10M6.4 13h3.2'], hand: ['M5.4 8.2V4.1a1 1 0 0 1 2 0v3.4-4.4a1 1 0 0 1 2 0v4.4-3.4a1 1 0 0 1 2 0v5.8a4.1 4.1 0 0 1-4.1 4.1h-.5a4 4 0 0 1-3.300-1.700L2.600 9.600a1 1 0 0 1 1.600-1.200z'],
    comment: ['M2.8 3.300h10.400v7.200H8l-3 2.500v-2.500H2.800z'], zoom: [['c', 7, 7, 4.2], 'M10.200 10.200l3.300 3.300'], search: [['c', 7, 7, 4.2], 'M10.200 10.200l3.300 3.300'],
    undo: ['M5.500 3.500l-3 3 3 3', 'M2.500 6.500h7a3.500 3.500 0 0 1 0 7H7'], redo: ['M10.500 3.500l3 3-3 3', 'M13.500 6.500h-7a3.500 3.500 0 0 0 0 7H9'],
    back: ['M10 3L5 8l5 5'], down: ['M4.500 6.300L8 9.800l3.500-3.500'], right: ['M6.300 4.500L9.800 8l-3.500 3.500'], plus: ['M8 3.200v9.600M3.200 8h9.600'], minus: ['M3.200 8h9.600'], close: ['M4 4l8 8M12 4l-8 8'],
    eye: ['M1.600 8S4 3.700 8 3.700 14.400 8 14.400 8 12 12.300 8 12.300 1.600 8 1.600 8z', ['c', 8, 8, 1.8]], eyeoff: ['M2.300 2.300l11.400 11.400', 'M6.400 4a6.300 6.300 0 0 1 1.600-.300c4 0 6.400 4.300 6.400 4.300a11.300 11.300 0 0 1-1.900 2.400M4.300 5.300A10.700 10.700 0 0 0 1.600 8S4 12.300 8 12.300c.700 0 1.300-.100 1.900-.300'],
    lock: [['r', 3.500, 7.200, 9, 6.300, 1.500], 'M5.500 7.200V5.200a2.500 2.500 0 0 1 5 0v2'], unlock: [['r', 3.500, 7.200, 9, 6.300, 1.500], 'M5.500 7.200V5.200a2.500 2.500 0 0 1 4.800-1'],
    group: [['r', 2.500, 2.500, 5.500, 5.500, 1], ['r', 8, 8, 5.500, 5.500, 1]], vector: ['M3.200 12.800C3.200 7 7 3.200 12.800 3.200', ['r', 1.800, 11.400, 2.800, 2.800, .5], ['r', 11.400, 1.800, 2.800, 2.800, .5]],
    image: [['r', 2.500, 3, 11, 10, 1.500], 'M2.800 11.200l3.400-3.400 2.800 2.800 1.900-1.900 2.400 2.400', ['c', 10.400, 6.100, .9]],
    component: ['M8 1.900l5.300 3.050v6.100L8 14.100l-5.300-3.050v-6.100z', ['c', 8, 8, 1.600]], instance: ['M8 1.900l5.300 3.050v6.100L8 14.100l-5.300-3.050v-6.100z'],
    section: [['r', 2.500, 3, 11, 10, 1.500], 'M2.500 6.200h11'], page: ['M4 2.500h5l3 3v8H4z', 'M9 2.500v3h3'],
    trash: ['M3 4.500h10M6.500 4.500V3h3v1.500M4.500 4.500l.500 8.500h6l.500-8.500'], dots: [['d', 3.500, 8], ['d', 8, 8], ['d', 12.500, 8]], grip: [['d', 6, 4.500], ['d', 10, 4.500], ['d', 6, 8], ['d', 10, 8], ['d', 6, 11.500], ['d', 10, 11.500]],
    share: ['M8 10V2.600M5.200 5.300L8 2.500l2.800 2.800M3 9.200v4.300h10V9.200'], export: ['M8 2.500V10M5.200 7.300L8 10.100l2.800-2.800M3 12.800h10'], play: ['M5.200 3.200l7.600 4.800-7.600 4.800z'],
    check: ['M3.400 8.400l3 3 6.200-7'], rotate: ['M12.600 8a4.600 4.600 0 1 1-1.700-3.600', 'M12.700 2.300v2.900H9.800'], radius: ['M3 13V8.200A5.200 5.200 0 0 1 8.200 3H13'],
    corners: ['M2.800 6V4.300a1.500 1.500 0 0 1 1.500-1.500H6M10 2.800h1.700a1.500 1.500 0 0 1 1.500 1.500V6M13.200 10v1.700a1.500 1.500 0 0 1-1.500 1.500H10M6 13.200H4.300a1.500 1.500 0 0 1-1.500-1.500V10'],
    opacity: [['c', 8, 8, 5.500], 'M8 2.500v11M10.500 3.200v9.600M12.600 5.200v5.600'], sun: [['c', 8, 8, 2.900], 'M8 1.500v1.600M8 12.900v1.600M1.500 8h1.600M12.900 8h1.600M3.400 3.400l1.100 1.100M11.500 11.500l1.100 1.100M3.400 12.600l1.100-1.100M11.500 4.500l1.100-1.100'],
    moon: ['M13 9.600A5.400 5.400 0 0 1 6.400 3 5.400 5.400 0 1 0 13 9.600z'], dropper: ['M9.800 3.300l2.900 2.900-1.400 1.400-2.900-2.900z', 'M8.900 5.600l-5.300 5.300-.6 2.100 2.100-.600 5.300-5.300'],
    tleft: ['M2.500 4h11M2.500 8h7M2.500 12h9'], tcenter: ['M2.500 4h11M4.500 8h7M3.500 12h9'], tright: ['M2.500 4h11M6.500 8h7M4.500 12h9'], tjust: ['M2.500 4h11M2.500 8h11M2.500 12h11'],
    vtop: ['M2.500 3h11M8 13.200V6M5.400 8.600L8 6l2.600 2.600'], vmid: ['M2.500 8h11M8 2v3.400M8 14v-3.400M6.200 3.800L8 5.600l1.800-1.800M6.200 12.200L8 10.400l1.800 1.800'], vbot: ['M2.500 13h11M8 2.800V10M5.400 7.400L8 10l2.600-2.600'],
    autow: ['M2 8h12M4.600 5.400L2 8l2.600 2.600M11.400 5.400L14 8l-2.600 2.600'], autoh: ['M3 3h10M3 6.500h10M3 10h6M12 9v5M10.200 12.200L12 14l1.800-1.800'], fixed: [['r', 2.500, 3.500, 11, 9, 1], 'M5 6.500h6M5 9.500h4'],
    lh: ['M2.500 3v10M1 4.500L2.500 3 4 4.500M1 11.500L2.500 13 4 11.500M7 4.500h7M7 8h7M7 11.500h5'], ls: ['M2 3v10M14 3v10M5.500 11l2.500-6 2.500 6M6.400 9h3.200'],
    hdir: ['M2.800 8h10.400M10.400 5.200L13.200 8l-2.800 2.800'], vdir: ['M8 2.800v10.400M5.200 10.400L8 13.200l2.800-2.800'], wrap: ['M2.800 4.500h8.200a2.700 2.700 0 0 1 0 5.400H5.500', 'M7.400 7.800L5.300 9.900l2.100 2.100'],
    gap: ['M3 3v10M13 3v10M6.500 8h3'], padh: ['M2.500 3v10M13.500 3v10', ['r', 5.500, 5.500, 5, 5, 1]], padv: ['M3 2.500h10M3 13.500h10', ['r', 5.500, 5.500, 5, 5, 1]],
    alL: ['M2.500 2v12', ['r', 4.500, 3.800, 8, 3.200, .8], ['r', 4.500, 9, 5, 3.200, .8]], alH: ['M8 2v12', ['r', 3.500, 3.800, 9, 3.200, .8], ['r', 5, 9, 6, 3.200, .8]], alR: ['M13.500 2v12', ['r', 3.500, 3.800, 8, 3.200, .8], ['r', 6.500, 9, 5, 3.200, .8]],
    alT: ['M2 2.500h12', ['r', 3.800, 4.500, 3.200, 8, .8], ['r', 9, 4.500, 3.200, 5, .8]], alV: ['M2 8h12', ['r', 3.800, 3.500, 3.200, 9, .8], ['r', 9, 5, 3.200, 6, .8]], alB: ['M2 13.500h12', ['r', 3.800, 3.500, 3.200, 8, .8], ['r', 9, 6.500, 3.200, 5, .8]],
    distH: ['M2.500 2v12M13.500 2v12', ['r', 6.300, 4.500, 3.400, 7, .8]], distV: ['M2 2.500h12M2 13.500h12', ['r', 4.500, 6.300, 7, 3.400, .8]], tidy: [['r', 2.500, 2.500, 4.200, 4.200, .8], ['r', 9.300, 2.500, 4.200, 4.200, .8], ['r', 2.500, 9.300, 4.200, 4.200, .8], ['r', 9.300, 9.300, 4.200, 4.200, .8]],
    flipH: ['M8 2v12', 'M5.800 4.500L2.500 8l3.300 3.500z', 'M10.200 4.500L13.500 8l-3.300 3.500z'], flipV: ['M2 8h12', 'M4.500 5.800L8 2.500l3.500 3.300z', 'M4.500 10.200L8 13.500l3.500-3.300z'],
    star2: ['M8 1.900l1.800 3.900 4.200.5-3.100 2.900.8 4.200L8 11.300l-3.700 2.100.8-4.200L2 6.300l4.200-.5z'], home: ['M2.800 7.600L8 3l5.200 4.600V13H9.700V9.700H6.300V13H2.800z'], copy: [['r', 5.500, 5.500, 8, 8, 1.500], 'M3.500 10.500h-.500a.500.500 0 0 1-.500-.500V3a.500.500 0 0 1 .500-.500h7a.500.500 0 0 1 .500.500v.500'],
    sliders: ['M2.500 5h6M11.500 5h2M2.500 11h2M7.500 11h6', ['c', 10, 5, 1.500], ['c', 6, 11, 1.500]], keys: [['r', 1.800, 4, 12.400, 8, 1.500], 'M4.500 7h.01M7 7h.01M9.500 7h.01M12 7h.01M5 9.800h6'], menu: ['M2.800 4.500h10.400M2.800 8h10.400M2.800 11.500h10.400'],
    sidebar: [['r', 2.200, 3, 11.600, 10, 1.500], 'M6 3v10'], link: ['M6.800 9.200l2.400-2.400M7.200 4.800l1-1a2.500 2.500 0 0 1 3.500 3.500l-1 1M8.800 11.200l-1 1a2.500 2.500 0 0 1-3.500-3.500l1-1'], clip: [['r', 3, 3, 10, 10, 1.500], 'M6 8h4'],
    spark: ['M8 2l1.300 3.700L13 7l-3.700 1.300L8 12l-1.300-3.700L3 7l3.700-1.300z', 'M12.500 11v2.500M11.200 12.200h2.600'], cloud: ['M4.600 12.200h6.600a2.700 2.700 0 0 0 .400-5.400 3.900 3.900 0 0 0-7.500.900 2.300 2.300 0 0 0 .500 4.500z'], history: ['M2.800 8a5.200 5.200 0 1 0 1.700-3.800', 'M2.500 3v2.600h2.600M8 5.200V8l1.900 1.300']
  };
  function icon(name, sizePx) {
    const s = document.createElementNS(NS, 'svg'); s.setAttribute('viewBox', '0 0 16 16'); s.setAttribute('width', sizePx || 16); s.setAttribute('height', sizePx || 16);
    s.setAttribute('fill', 'none'); s.setAttribute('stroke', 'currentColor'); s.setAttribute('stroke-width', '1.4'); s.setAttribute('stroke-linecap', 'round'); s.setAttribute('stroke-linejoin', 'round'); s.setAttribute('aria-hidden', 'true'); s.setAttribute('class', 'hd-ic');
    for (const part of (I[name] || I.rect)) { let el;
      if (typeof part === 'string') { el = document.createElementNS(NS, 'path'); el.setAttribute('d', part); }
      else if (part[0] === 'r') { el = document.createElementNS(NS, 'rect'); el.setAttribute('x', part[1]); el.setAttribute('y', part[2]); el.setAttribute('width', part[3]); el.setAttribute('height', part[4]); el.setAttribute('rx', part[5]); }
      else if (part[0] === 'c') { el = document.createElementNS(NS, 'circle'); el.setAttribute('cx', part[1]); el.setAttribute('cy', part[2]); el.setAttribute('r', part[3]); }
      else { el = document.createElementNS(NS, 'circle'); el.setAttribute('cx', part[1]); el.setAttribute('cy', part[2]); el.setAttribute('r', 1); el.setAttribute('fill', 'currentColor'); el.setAttribute('stroke', 'none'); }
      s.appendChild(el); }
    return s;
  }
  const TYPE_ICON = {FRAME: 'frame', GROUP: 'group', SECTION: 'section', RECT: 'rect', ELLIPSE: 'ellipse', LINE: 'line', POLYGON: 'polygon', STAR: 'star', VECTOR: 'vector', TEXT: 'text', COMPONENT: 'component', COMPONENT_SET: 'component', INSTANCE: 'instance', PAGE: 'page'};
  function ibtn(name, title, run, cls) { const b = h('button', {class: 'hd-ib' + (cls ? ' ' + cls : ''), type: 'button', title: title, 'aria-label': title}, icon(name)); if (run) b.addEventListener('click', run); return b; }

  /* ---------------------------------------------------------------- server */
  let TOKEN = ''; try { TOKEN = localStorage.getItem('hoola.console.token') || ''; } catch (e) { /* private window */ }
  function isBinary(b) { return (typeof Blob !== 'undefined' && b instanceof Blob) || b instanceof ArrayBuffer || ArrayBuffer.isView(b); }
  async function api(method, path, body) {
    const url = /^\/api\//.test(path) ? path : '/api/design' + (path.charAt(0) === '/' ? '' : '/') + path;
    const headers = {Authorization: 'Bearer ' + TOKEN}; let payload;
    if (body !== undefined && body !== null) { if (isBinary(body)) { headers['Content-Type'] = (body.type) || 'application/octet-stream'; payload = body; } else { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); } }
    const r = await fetch(url, {method: method, headers: headers, body: payload, credentials: 'omit', cache: 'no-store'});
    if (r.status === 401) { location.replace('/console/'); throw new Error('Please sign in again.'); }
    const ct = r.headers.get('content-type') || ''; let data = null;
    if (/json/.test(ct)) { try { data = await r.json(); } catch (e) { data = null; } } else if (r.ok && method === 'GET') { try { data = await r.blob(); } catch (e) { data = null; } }
    if (!r.ok) { const bad = data && Array.isArray(data.detail) && data.detail[0];
      throw new Error((data && ((typeof data.detail === 'string' ? data.detail : '') || data.error || data.message)) || (bad ? String(bad.msg) : '') || 'The server refused the request (' + r.status + ')'); }
    return data;
  }
  let toastEl = null, toastT = 0;
  function toast(msg, bad) { if (!toastEl) { toastEl = h('div', {class: 'hd-toast', role: 'status', 'aria-live': 'polite'}); document.body.appendChild(toastEl); }
    toastEl.textContent = String(msg); toastEl.className = 'hd-toast' + (bad ? ' bad' : '') + ' on'; clearTimeout(toastT); toastT = setTimeout(() => { toastEl.className = 'hd-toast'; }, 4200); }

  /* ---------------------------------------------------------------- hooks for later phases */
  const hooks = {}; const HOOK_SOON = {share: 'Sharing', export: 'Export', present: 'Present', comment: 'Comments', importSvg: 'SVG import', ai: 'Hoola AI', versions: 'Version history'};
  function hook(name, fn) { hooks[name] = fn; refresh(); }
  function fire(name) { const fn = hooks[name], args = Array.prototype.slice.call(arguments, 1); if (fn) { try { return fn.apply(null, args); } catch (e) { toast(e.message || String(e), true); return undefined; } }
    if (HOOK_SOON[name]) toast(HOOK_SOON[name] + ' is not switched on in this build yet.'); return undefined; }

  /* ---------------------------------------------------------------- popovers + menus */
  const pops = [];
  function closePops(from) { while (pops.length > (from || 0)) { const p = pops.pop(); if (p.el.parentNode) p.el.parentNode.removeChild(p.el); if (p.onClose) { try { p.onClose(); } catch (e) { /* closing must not throw */ } } if (p.focus && p.focus.focus && document.contains(p.focus)) { try { p.focus.focus({preventScroll: true}); } catch (e) { /* gone */ } } } }
  function place(el, anchor, side) {
    const vw = innerWidth, vh = innerHeight; el.style.left = '0px'; el.style.top = '0px'; const w = el.offsetWidth, hh = el.offsetHeight; let x, y;
    if (anchor && anchor.getBoundingClientRect) { const r = anchor.getBoundingClientRect();
      if (side === 'left') { x = r.left - w - 8; y = r.top - 8; if (x < 8) x = r.right + 8; }
      else if (side === 'right') { x = r.right + 4; y = r.top - 4; if (x + w > vw - 8) x = r.left - w - 4; }
      else { x = r.left; y = r.bottom + 6; if (y + hh > vh - 8 && r.top - hh - 6 > 8) y = r.top - hh - 6; } }
    else { x = anchor.x; y = anchor.y; }
    el.style.left = Math.round(clamp(x, 8, Math.max(8, vw - w - 8))) + 'px'; el.style.top = Math.round(clamp(y, 8, Math.max(8, vh - hh - 8))) + 'px';
  }
  function pop(anchor, content, o) {
    o = o || {}; closePops(o.level || 0);
    const el = h('div', {class: 'hd-pop ' + (o.cls || ''), role: o.role || 'dialog', 'aria-label': o.label || 'Options', tabIndex: -1}); add(el, content); document.body.appendChild(el);
    const p = {el: el, onClose: o.onClose, anchor: anchor, focus: o.keepFocus ? null : document.activeElement}; pops.push(p); place(el, anchor, o.side);
    if (!o.noFocus) { const f = el.querySelector('[autofocus], input, button, select'); (f || el).focus({preventScroll: true}); }
    return {el: el, close() { const i = pops.indexOf(p); if (i >= 0) closePops(i); }, place() { place(el, anchor, o.side); }};
  }
  document.addEventListener('pointerdown', ev => { if (!pops.length) return; for (let i = pops.length - 1; i >= 0; i--) { const p = pops[i]; if (p.el.contains(ev.target) || (p.anchor && p.anchor.contains && p.anchor.contains(ev.target) && i === pops.length - 1)) { closePops(i + 1); return; } } closePops(0); }, true);
  window.addEventListener('resize', () => closePops(0));
  function keyParts(combo) { if (!combo) return []; const plus = combo.slice(-1) === '+', list = (plus ? combo.slice(0, -1) : combo).split('+').filter(Boolean); if (plus) list.push('+');
    return list.map(k => k === 'mod' ? (MAC ? '\u2318' : 'Ctrl') : k === 'shift' ? (MAC ? '\u21E7' : 'Shift') : k === 'alt' ? (MAC ? '\u2325' : 'Alt') : k === 'delete' ? 'Del' : k === 'escape' ? 'Esc' : k.length === 1 ? k.toUpperCase() : k.charAt(0).toUpperCase() + k.slice(1)); }
  function keysLabel(combo) { return keyParts(combo).join(MAC ? ' ' : '+'); }
  /* items: {label, keys, icon, run, checked, disabled, danger, sub:[...]} or '-' */
  function menu(anchor, items, o) {
    o = o || {}; const list = h('div', {class: 'hd-menu', role: 'menu'}); let handle = null;
    items = items.filter(Boolean); while (items.length && items[0] === '-') items.shift(); while (items.length && items[items.length - 1] === '-') items.pop();
    items.forEach((it, i) => {
      if (it === '-') { if (items[i - 1] !== '-') list.appendChild(h('div', {class: 'hd-msep', role: 'separator'})); return; }
      if (it.head) { list.appendChild(h('div', {class: 'hd-mhead', text: it.head})); return; }
      const b = h('button', {class: 'hd-mi' + (it.danger ? ' danger' : ''), type: 'button', role: it.checked !== undefined ? 'menuitemcheckbox' : 'menuitem', disabled: !!it.disabled, 'aria-checked': it.checked !== undefined ? String(!!it.checked) : null},
        h('span', {class: 'hd-mic'}, it.checked ? icon('check') : it.icon ? icon(it.icon) : null), h('span', {class: 'hd-mlab', text: it.label}), it.keys ? h('span', {class: 'hd-mkeys', text: keysLabel(it.keys)}) : it.hint ? h('span', {class: 'hd-mkeys', text: it.hint}) : null, it.sub ? icon('right') : null);
      b.addEventListener('click', () => { if (it.sub) { menu(b, it.sub, {level: (o.level || 0) + 1, side: 'right'}); return; } if (handle) closePops(o.level || 0); if (it.run) it.run(); });
      list.appendChild(b);
    });
    list.addEventListener('keydown', ev => { const bs = Array.from(list.querySelectorAll('.hd-mi:not(:disabled)')), i = bs.indexOf(document.activeElement);
      if (ev.key === 'ArrowDown') { ev.preventDefault(); (bs[(i + 1) % bs.length] || bs[0]).focus(); } else if (ev.key === 'ArrowUp') { ev.preventDefault(); (bs[(i - 1 + bs.length) % bs.length] || bs[0]).focus(); }
      else if (ev.key === 'Home') { ev.preventDefault(); if (bs[0]) bs[0].focus(); } else if (ev.key === 'End') { ev.preventDefault(); if (bs.length) bs[bs.length - 1].focus(); } });
    handle = pop(anchor, list, {cls: 'hd-pop-menu', role: 'presentation', label: o.label || 'Menu', level: o.level || 0, side: o.side});
    return handle;
  }

  /* ---------------------------------------------------------------- commands + shortcuts */
  const commands = [], shortcuts = {}, menus = {};
  function norm(combo) { const parts = String(combo).toLowerCase().replace(/\s+/g, '').replace('cmd', 'mod').replace('ctrl', 'mod').split('+').filter(Boolean); const key = parts.filter(p => p !== 'mod' && p !== 'shift' && p !== 'alt').pop() || '';
    return (parts.indexOf('mod') >= 0 ? 'mod+' : '') + (parts.indexOf('alt') >= 0 ? 'alt+' : '') + (parts.indexOf('shift') >= 0 ? 'shift+' : '') + (combo.slice(-1) === '+' ? '+' : key); }
  function registerShortcut(combo, fn, label) { for (const c of [].concat(combo)) shortcuts[norm(c)] = {fn: fn, label: label || ''}; }
  /* {id, label, group, keys, run, when, edit} - shows in the palette, the shortcut sheet and (with keys) on the keyboard */
  function command(c) { const i = commands.findIndex(x => x.id === c.id); if (i >= 0) commands[i] = c; else commands.push(c); if (c.keys) registerShortcut(c.keys, () => runCmd(c), c.label); return c; }
  function runCmd(c) { if (typeof c === 'string') c = commands.find(x => x.id === c); if (!c) return false; if (c.when && !c.when()) return false; if (c.edit && !U().canEdit()) { toast('This file is view only.'); return true; } c.run(); return true; }
  function registerMenu(where, item) { (menus[where] = menus[where] || []).push(item); }
  const CODE_KEY = {BracketLeft: '[', BracketRight: ']', Backslash: '\\', Slash: '/', Equal: '=', Minus: '-', Comma: ',', Period: '.', Backspace: 'backspace', Delete: 'delete', Enter: 'enter', Escape: 'escape', Space: 'space', Tab: 'tab', NumpadAdd: '+', NumpadSubtract: '-'};
  function combosOf(ev) { const mods = (ev.ctrlKey || ev.metaKey ? 'mod+' : '') + (ev.altKey ? 'alt+' : ''), out = []; const code = ev.code || '';
    let ck = CODE_KEY[code]; if (!ck && /^Key[A-Z]$/.test(code)) ck = code.slice(3).toLowerCase(); if (!ck && /^Digit\d$/.test(code)) ck = code.slice(5); if (!ck && /^Numpad\d$/.test(code)) ck = code.slice(6);
    if (ck) out.push(mods + (ev.shiftKey ? 'shift+' : '') + ck);
    const k = (ev.key || '').toLowerCase(); if (k && k.length === 1) { out.push(mods + (ev.shiftKey ? 'shift+' : '') + k); out.push(mods + k); } else if (k && !ck) out.push(mods + (ev.shiftKey ? 'shift+' : '') + k);
    return out; }
  function typing(ev) { const t = ev.target; return !!(t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)); }

  /* ---------------------------------------------------------------- colour */
  function hexOk(s) { return /^#[0-9a-f]{6}$/i.test(s); }
  function parseColor(s) {
    s = String(s || '').trim(); let m = /^#?([0-9a-f]{3,8})$/i.exec(s);
    if (m) { let x = m[1]; if (x.length === 3 || x.length === 4) x = x.split('').map(c => c + c).join(''); if (x.length === 6 || x.length === 8) return {hex: '#' + x.slice(0, 6).toUpperCase(), a: x.length === 8 ? parseInt(x.slice(6), 16) / 255 : null}; if (x.length < 6) { x = (x + x + x + x + x + x).slice(0, 6); return {hex: '#' + x.toUpperCase(), a: null}; } }
    m = /^rgba?\(?\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)(?:[\s,/]+([\d.]+%?))?\s*\)?$/i.exec(s);
    if (m) { const a = m[4] ? (/%$/.test(m[4]) ? parseFloat(m[4]) / 100 : parseFloat(m[4])) : null; return {hex: rgbHex(+m[1], +m[2], +m[3]), a: a === null ? null : clamp(a, 0, 1)}; }
    return null;
  }
  function rgbHex(r, g, b) { return '#' + [r, g, b].map(v => clamp(Math.round(v), 0, 255).toString(16).padStart(2, '0')).join('').toUpperCase(); }
  function hexRgb(hex) { const x = hexOk(hex) ? hex.slice(1) : '000000'; return [parseInt(x.slice(0, 2), 16), parseInt(x.slice(2, 4), 16), parseInt(x.slice(4, 6), 16)]; }
  function rgbHsv(r, g, b) { r /= 255; g /= 255; b /= 255; const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn; let hh = 0;
    if (d) { if (mx === r) hh = ((g - b) / d) % 6; else if (mx === g) hh = (b - r) / d + 2; else hh = (r - g) / d + 4; hh *= 60; if (hh < 0) hh += 360; } return [hh, mx ? d / mx : 0, mx]; }
  function hsvRgb(hh, s, v) { const c = v * s, x = c * (1 - Math.abs((hh / 60) % 2 - 1)), m = v - c; let r = 0, g = 0, b = 0;
    if (hh < 60) { r = c; g = x; } else if (hh < 120) { r = x; g = c; } else if (hh < 180) { g = c; b = x; } else if (hh < 240) { g = x; b = c; } else if (hh < 300) { r = x; b = c; } else { r = c; b = x; }
    return [(r + m) * 255, (g + m) * 255, (b + m) * 255]; }
  function rgba(hex, a) { const c = hexRgb(hex); return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + (a === undefined || a === null ? 1 : Math.round(a * 1000) / 1000) + ')'; }
  function gradCss(p, flat) { const stops = (p.stops || []).slice().sort((a, b) => a.pos - b.pos).map(s => rgba(s.color, s.opacity === undefined ? 1 : s.opacity) + ' ' + fmt(s.pos * 100, 1) + '%').join(', ') || 'transparent, transparent';
    if (flat || p.type === 'linear') { let ang = 90; if (!flat && p.from && p.to) ang = Math.atan2(p.to[1] - p.from[1], p.to[0] - p.from[0]) * 180 / Math.PI + 90; return 'linear-gradient(' + fmt(ang, 1) + 'deg, ' + stops + ')'; }
    if (p.type === 'radial') return 'radial-gradient(circle at ' + fmt((p.from ? p.from[0] : 0.5) * 100, 0) + '% ' + fmt((p.from ? p.from[1] : 0.5) * 100, 0) + '%, ' + stops + ')';
    return 'conic-gradient(from 90deg, ' + stops + ')'; }
  function paintSwatch(el, p) {
    const c = el.firstChild || el.appendChild(h('span', {class: 'hd-swc'})); c.style.backgroundImage = ''; c.style.backgroundColor = 'transparent'; clear(c);
    if (!p || p === MIXED) { c.style.backgroundImage = 'linear-gradient(135deg, var(--hair2) 50%, var(--sunk) 50%)'; return; }
    if (p.type === 'solid') c.style.backgroundColor = rgba(p.color, p.opacity === undefined ? 1 : p.opacity);
    else if (p.type === 'image') { const img = HD.render && HD.render.image ? HD.render.image(p.hash) : null; if (img && img.src) { c.style.backgroundImage = 'url("' + String(img.src).replace(/["\\]/g, '') + '")'; c.style.backgroundSize = 'cover'; c.style.backgroundPosition = 'center'; } else { c.appendChild(icon('image', 12)); if (p.hash && (paintSwatch.tries = (paintSwatch.tries || 0) + 1) < 40) setTimeout(() => { ui.sig = ''; refresh(); }, 700); } }
    else c.style.backgroundImage = gradCss(p);
  }
  const RECENT_KEY = 'hoola.design.recent';
  function recent() { try { return (JSON.parse(localStorage.getItem(RECENT_KEY) || '[]') || []).filter(hexOk).slice(0, 14); } catch (e) { return []; } }
  function pushRecent(hex) { if (!hexOk(hex)) return; const r = recent().filter(c => c !== hex.toUpperCase()); r.unshift(hex.toUpperCase()); try { localStorage.setItem(RECENT_KEY, JSON.stringify(r.slice(0, 14))); } catch (e) { /* private window */ } }
  function docColors() { const seen = new Set(), out = []; let n = 0; const stack = [HD.sel.page];
    while (stack.length && n < 3000 && out.length < 14) { const id = stack.pop(); for (const k of HD.store.children(id)) { n++; const nd = HD.store.get(k); if (!nd) continue;
      for (const arr of [nd.fills, nd.strokes]) if (Array.isArray(arr)) for (const p of arr) if (p && p.type === 'solid' && hexOk(p.color) && !seen.has(p.color.toUpperCase())) { seen.add(p.color.toUpperCase()); out.push(p.color.toUpperCase()); }
      stack.push(k); } }
    return out.slice(0, 14); }
  function drag(el, onMove, onEnd, onStart) {
    el.addEventListener('pointerdown', ev => { if (ev.button) return; ev.preventDefault(); try { el.setPointerCapture(ev.pointerId); } catch (e) { /* synthetic */ }
      const st = onStart ? onStart(ev) : null; if (st === false) return; onMove(ev, st);
      const mv = e2 => onMove(e2, st), up = e2 => { el.removeEventListener('pointermove', mv); el.removeEventListener('pointerup', up); el.removeEventListener('pointercancel', up); try { el.releasePointerCapture(ev.pointerId); } catch (e) { /* released */ } if (onEnd) onEnd(e2, st); };
      el.addEventListener('pointermove', mv); el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up); });
  }
  const GRAD_DIRS = [[[0.5, 0], [0.5, 1]], [[1, 0.5], [0, 0.5]], [[0.5, 1], [0.5, 0]], [[0, 0.5], [1, 0.5]]];
  /* o: {get() -> paint, set(paint, gesture|null), solidOnly, title, level, side} */
  function paintPicker(anchor, o) {
    let stop = 0, hue = 0, g = null, lastHex = '';
    const cur = () => { const p = o.get(); return p && p !== MIXED ? JSON.parse(JSON.stringify(p)) : {type: 'solid', color: '#D9D9D9', opacity: 1, visible: true}; };
    const isGrad = p => p.type === 'linear' || p.type === 'radial' || p.type === 'angular';
    const colOf = p => { if (isGrad(p)) { const s = (p.stops || [])[Math.min(stop, (p.stops || []).length - 1)] || {color: '#000000', opacity: 1}; return {hex: s.color, a: s.opacity === undefined ? 1 : s.opacity}; } return {hex: p.color || '#000000', a: p.opacity === undefined ? 1 : p.opacity}; };
    const change = (fn, viaG) => { const p = cur(); fn(p); o.set(p, viaG ? g : null); sync(); };
    const setCol = (hex, a, viaG) => change(p => { if (isGrad(p)) { const s = p.stops[Math.min(stop, p.stops.length - 1)]; if (hex) s.color = hex; if (a !== null && a !== undefined) s.opacity = a; } else if (p.type === 'solid') { if (hex) p.color = hex; if (a !== null && a !== undefined) p.opacity = a; } else if (a !== null && a !== undefined) p.opacity = a; }, viaG);
    const begin = label => { g = new (U().Gesture)(label || 'Colour'); }, end = () => { if (g) g.end(); g = null; const c = colOf(cur()); pushRecent(c.hex); };
    const root = h('div', {class: 'hd-picker'});
    const types = o.solidOnly ? null : h('div', {class: 'hd-seg hd-ptypes', role: 'tablist', 'aria-label': 'Paint type'});
    const TYPES = [['solid', 'Solid'], ['linear', 'Linear'], ['radial', 'Radial'], ['angular', 'Sweep'], ['image', 'Image']];
    if (types) for (const t of TYPES) types.appendChild(h('button', {type: 'button', class: 'hd-segb', role: 'tab', 'data-v': t[0], text: t[1], on: {click: () => setType(t[0])}}));
    const gbar = h('div', {class: 'hd-gbar', title: 'Click to add a colour stop'}), gwrap = h('div', {class: 'hd-gwrap'}, gbar,
      h('div', {class: 'hd-grow'}, ibtn('rotate', 'Rotate the gradient 90\u00B0', () => change(p => { const i = GRAD_DIRS.findIndex(d => p.from && p.to && Math.abs(d[0][0] - p.from[0]) < 0.01 && Math.abs(d[0][1] - p.from[1]) < 0.01 && Math.abs(d[1][0] - p.to[0]) < 0.01); const n = GRAD_DIRS[(i + 1) % 4]; p.from = n[0].slice(); p.to = n[1].slice(); })),
        ibtn('flipH', 'Reverse the stops', () => change(p => { p.stops.forEach(s => { s.pos = 1 - s.pos; }); p.stops.sort((a, b) => a.pos - b.pos); stop = p.stops.length - 1 - stop; })),
        ibtn('minus', 'Remove the selected stop', () => change(p => { if (p.stops.length > 2) { p.stops.splice(stop, 1); stop = Math.max(0, stop - 1); } }))));
    const sv = h('div', {class: 'hd-sv', role: 'slider', 'aria-label': 'Saturation and brightness', tabIndex: 0}, h('i', {class: 'hd-svdot'}));
    const hueEl = h('div', {class: 'hd-hue', role: 'slider', 'aria-label': 'Hue', tabIndex: 0}, h('i', {class: 'hd-sdot'}));
    const alEl = h('div', {class: 'hd-alpha', role: 'slider', 'aria-label': 'Opacity', tabIndex: 0}, h('span', {class: 'hd-alfill'}), h('i', {class: 'hd-sdot'}));
    const hexIn = h('input', {class: 'hd-in', type: 'text', 'aria-label': 'Hex or RGB colour', spellcheck: 'false', maxlength: '24'}), opIn = h('input', {class: 'hd-in hd-pop-op', type: 'text', 'aria-label': 'Opacity percent', inputmode: 'decimal'});
    const dropper = window.EyeDropper ? ibtn('dropper', 'Pick a colour from the screen', () => { try { new window.EyeDropper().open().then(r => { const c = parseColor(r.sRGBHex); if (c) { setCol(c.hex, null); pushRecent(c.hex); } }).catch(() => {}); } catch (e) { /* cancelled */ } }) : null;
    const colorPart = h('div', {class: 'hd-pcolor'}, sv, h('div', {class: 'hd-prow'}, dropper, h('div', {class: 'hd-sliders'}, hueEl, alEl)), h('div', {class: 'hd-prow'}, h('span', {class: 'hd-plab', text: 'Hex'}), hexIn, opIn));
    const swDoc = h('div', {class: 'hd-swatches'}), swRec = h('div', {class: 'hd-swatches'});
    const lists = h('div', {class: 'hd-plists'}, h('div', {class: 'hd-plab2', text: 'On this page'}), swDoc, h('div', {class: 'hd-plab2', text: 'Recent'}), swRec);
    const file = h('input', {type: 'file', accept: 'image/png,image/jpeg,image/webp,image/gif,image/svg+xml', hidden: true, 'aria-hidden': 'true', tabIndex: -1});
    const imgPrev = h('div', {class: 'hd-imgprev'}), modeSel = h('select', {class: 'hd-sel', 'aria-label': 'Image fit'}, ['fill', 'fit', 'crop', 'tile'].map(m => h('option', {value: m, text: m.charAt(0).toUpperCase() + m.slice(1)})));
    const imgPart = h('div', {class: 'hd-pimage'}, imgPrev, h('div', {class: 'hd-prow'}, h('button', {class: 'hd-btn', type: 'button', text: 'Choose image\u2026', on: {click: () => file.click()}}), modeSel), file,
      h('div', {class: 'hd-prow'}, h('span', {class: 'hd-plab', text: 'Opacity'})));
    const imgOp = h('input', {class: 'hd-in', type: 'text', 'aria-label': 'Image opacity percent'}); imgPart.lastChild.appendChild(imgOp);
    add(root, [h('div', {class: 'hd-phead'}, h('span', {class: 'hd-ptitle', text: o.title || 'Colour'}), ibtn('close', 'Close', () => handle.close())), types, gwrap, colorPart, imgPart, lists]);
    function setType(t) { const p = cur(); if (p.type === t) return; const c = colOf(p);
      if (t === 'image') { root.dataset.type = 'image'; sync('image'); if (p.type !== 'image') file.click(); return; }
      if (t === 'solid') { o.set({type: 'solid', color: p.type === 'image' ? '#D9D9D9' : c.hex, opacity: p.type === 'image' ? 1 : c.a, visible: p.visible !== false}, null); stop = 0; sync(); return; }
      const base = isGrad(p) ? p.stops : [{pos: 0, color: p.type === 'image' ? '#6E55F0' : c.hex, opacity: 1}, {pos: 1, color: p.type === 'image' ? '#EE8F35' : c.hex, opacity: p.type === 'image' ? 1 : 0}];
      o.set({type: t, stops: base, from: t === 'linear' ? [0.5, 0] : [0.5, 0.5], to: t === 'linear' ? [0.5, 1] : [1, 0.5], opacity: 1, visible: p.visible !== false}, null); sync(); }
    file.addEventListener('change', () => { const f = file.files && file.files[0]; file.value = ''; if (!f) return; uploadImage(f).then(hash => { if (!hash) return; const p = cur(); o.set({type: 'image', hash: hash, mode: p.mode || 'fill', opacity: p.type === 'image' && p.opacity !== undefined ? p.opacity : 1, visible: p.visible !== false}, null); setTimeout(sync, 300); sync(); }); });
    modeSel.addEventListener('change', () => change(p => { if (p.type === 'image') p.mode = modeSel.value; }));
    imgOp.addEventListener('change', () => { const v = parseFloat(imgOp.value); if (isFinite(v)) change(p => { p.opacity = clamp(v / 100, 0, 1); }); else sync(); });
    drag(sv, ev => { const r = sv.getBoundingClientRect(), s = clamp((ev.clientX - r.left) / r.width, 0, 1), v = 1 - clamp((ev.clientY - r.top) / r.height, 0, 1), c = hsvRgb(hue, s, v); setCol(rgbHex(c[0], c[1], c[2]), null, true); }, end, () => begin());
    drag(hueEl, ev => { const r = hueEl.getBoundingClientRect(); hue = clamp((ev.clientX - r.left) / r.width, 0, 1) * 359.9; const c0 = colOf(cur()), k = hexRgb(c0.hex), hsv = rgbHsv(k[0], k[1], k[2]), c = hsvRgb(hue, hsv[1] || (hsv[2] ? 0 : 0), hsv[2]); setCol(rgbHex(c[0], c[1], c[2]), null, true); }, end, () => begin());
    drag(alEl, ev => { const r = alEl.getBoundingClientRect(); setCol(null, Math.round(clamp((ev.clientX - r.left) / r.width, 0, 1) * 100) / 100, true); }, end, () => begin('Opacity'));
    const keyStep = (el, fn) => el.addEventListener('keydown', ev => { const d = ev.key === 'ArrowRight' || ev.key === 'ArrowUp' ? 1 : ev.key === 'ArrowLeft' || ev.key === 'ArrowDown' ? -1 : 0; if (!d) return; ev.preventDefault(); fn(d * (ev.shiftKey ? 10 : 1), ev.key); });
    keyStep(hueEl, d => { hue = (hue + d * 3 + 360) % 360; const k = hexRgb(colOf(cur()).hex), hsv = rgbHsv(k[0], k[1], k[2]), c = hsvRgb(hue, hsv[1], hsv[2]); setCol(rgbHex(c[0], c[1], c[2]), null); });
    keyStep(alEl, d => setCol(null, clamp(colOf(cur()).a + d * 0.01, 0, 1)));
    keyStep(sv, (d, key) => { const k = hexRgb(colOf(cur()).hex), hsv = rgbHsv(k[0], k[1], k[2]); if (key === 'ArrowLeft' || key === 'ArrowRight') hsv[1] = clamp(hsv[1] + d * 0.01, 0, 1); else hsv[2] = clamp(hsv[2] + d * 0.01, 0, 1); const c = hsvRgb(hue, hsv[1], hsv[2]); setCol(rgbHex(c[0], c[1], c[2]), null); });
    hexIn.addEventListener('change', () => { const c = parseColor(hexIn.value); if (c) { setCol(c.hex, c.a); pushRecent(c.hex); } else sync(); });
    hexIn.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); hexIn.blur(); hexIn.focus(); hexIn.select(); } });
    opIn.addEventListener('change', () => { const v = parseFloat(opIn.value); if (isFinite(v)) setCol(null, clamp(v / 100, 0, 1)); else sync(); });
    gbar.addEventListener('pointerdown', ev => { if (ev.target !== gbar) return; const r = gbar.getBoundingClientRect(), pos = clamp((ev.clientX - r.left) / r.width, 0, 1);
      change(p => { const near = p.stops.slice().sort((a, b) => Math.abs(a.pos - pos) - Math.abs(b.pos - pos))[0] || {color: '#000000', opacity: 1}; p.stops.push({pos: Math.round(pos * 1000) / 1000, color: near.color, opacity: near.opacity === undefined ? 1 : near.opacity}); p.stops.sort((a, b) => a.pos - b.pos); stop = p.stops.findIndex(s => Math.abs(s.pos - pos) < 0.0006); if (stop < 0) stop = 0; }); });
    function swatches(el, list) { clear(el); if (!list.length) { el.appendChild(h('span', {class: 'hd-none', text: 'None yet'})); return; } for (const c of list) { const b = h('button', {class: 'hd-sw', type: 'button', title: c, 'aria-label': 'Use ' + c}); b.appendChild(h('span', {class: 'hd-swc', style: {backgroundColor: c}})); b.addEventListener('click', () => { setCol(c, null); }); el.appendChild(b); } }
    function sync(force) {
      const p = cur(), type = force || p.type; root.dataset.type = isGrad({type: type}) ? 'grad' : type; if (types) for (const b of types.children) { const on = b.dataset.v === type; b.classList.toggle('on', on); b.setAttribute('aria-selected', String(on)); }
      if (type === 'image') { clear(imgPrev); const img = p.type === 'image' && HD.render.image ? HD.render.image(p.hash) : null; if (img && img.src) imgPrev.style.backgroundImage = 'url("' + String(img.src).replace(/["\\]/g, '') + '")'; else { imgPrev.style.backgroundImage = ''; imgPrev.appendChild(h('span', {class: 'hd-none', text: p.type === 'image' ? 'Loading image\u2026' : 'No image yet'})); }
        modeSel.value = p.mode || 'fill'; if (document.activeElement !== imgOp) imgOp.value = fmt((p.type === 'image' && p.opacity !== undefined ? p.opacity : 1) * 100, 0) + '%'; return; }
      if (isGrad(p)) { stop = clamp(stop, 0, p.stops.length - 1); gbar.style.backgroundImage = gradCss(p, true); Array.from(gbar.children).forEach(c => c.remove());
        p.stops.forEach((s, i) => { const b = h('button', {class: 'hd-gstop' + (i === stop ? ' on' : ''), type: 'button', 'aria-label': 'Colour stop ' + (i + 1) + ' at ' + Math.round(s.pos * 100) + '%', style: {left: (s.pos * 100) + '%'}}, h('span', {style: {backgroundColor: s.color}}));
          drag(b, ev => { const r = gbar.getBoundingClientRect(), pos = Math.round(clamp((ev.clientX - r.left) / r.width, 0, 1) * 1000) / 1000; const q = cur(); if (!q.stops[stop] || q.stops[stop].pos === pos) return; q.stops[stop].pos = pos; o.set(q, g); b.style.left = (pos * 100) + '%'; gbar.style.backgroundImage = gradCss(q, true); }, () => { end(); sync(); }, () => { stop = i; begin('Gradient'); for (const x of gbar.children) x.classList.toggle('on', x === b); syncColor(cur()); });
          b.addEventListener('keydown', ev => { if ((ev.key === 'Delete' || ev.key === 'Backspace') && p.stops.length > 2) { ev.preventDefault(); stop = i; change(q => { q.stops.splice(i, 1); stop = Math.max(0, i - 1); }); } });
          gbar.appendChild(b); }); }
      syncColor(p); swatches(swDoc, docColors()); swatches(swRec, recent());
    }
    function syncColor(p) {
      const c = colOf(p), k = hexRgb(c.hex), hsv = rgbHsv(k[0], k[1], k[2]); if (c.hex !== lastHex) { if (hsv[1] > 0.001 && hsv[2] > 0.001) hue = hsv[0]; lastHex = c.hex; }
      const hc = hsvRgb(hue, 1, 1); sv.style.backgroundColor = rgbHex(hc[0], hc[1], hc[2]); sv.firstChild.style.left = (hsv[1] * 100) + '%'; sv.firstChild.style.top = ((1 - hsv[2]) * 100) + '%'; sv.firstChild.style.backgroundColor = c.hex;
      hueEl.firstChild.style.left = (hue / 360 * 100) + '%'; alEl.lastChild.style.left = (c.a * 100) + '%'; alEl.firstChild.style.backgroundImage = 'linear-gradient(90deg, ' + rgba(c.hex, 0) + ', ' + rgba(c.hex, 1) + ')';
      if (document.activeElement !== hexIn) hexIn.value = c.hex.slice(1); if (document.activeElement !== opIn) opIn.value = fmt(c.a * 100, 0) + '%';
    }
    const handle = pop(anchor, root, {cls: 'hd-pop-picker', label: o.title || 'Colour picker', level: o.level || 0, side: o.side || 'left', onClose: () => { if (g) g.end(); if (ui.paint === live) ui.paint = null; if (HD.render.invalidate) HD.render.invalidate(); if (o.onClose) o.onClose(); }});
    /* the paint being edited, for on-canvas handles (hd-vector.js): get() -> paint, set(paint, gesture|null), stop */
    const live = {get: cur, set: (p, viaG) => { o.set(p, viaG || null); sync(); }, get stop() { return stop; }, set stop(i) { stop = i; sync(); }, level: o.level || 0, solidOnly: !!o.solidOnly};
    ui.paint = live; if (HD.render.invalidate) HD.render.invalidate();
    sync(); handle.place(); handle.sync = sync; return handle;
  }
  async function uploadImage(fileOrBlob) {
    const f = HD.app && HD.app.file; if (!f) return null; if (fileOrBlob.size > 10 * 1024 * 1024) { toast('That image is over 10 MB.', true); return null; }
    try { const r = await api('POST', '/files/' + encodeURIComponent(f.id) + '/assets', fileOrBlob); return r && r.hash ? r.hash : null; } catch (e) { toast(e.message || 'The image could not be uploaded.', true); return null; }
  }

  /* ---------------------------------------------------------------- small maths for number boxes (no eval) */
  function calc(text, base, unit) {
    let s = String(text).replace(/,/g, '.').replace(/[\u00D7x]/gi, '*').replace(/px|\u00B0/gi, '').trim(); if (unit === '%') s = s.replace(/%/g, ''); if (!s) return null;
    let i = 0; const peek = () => { while (s.charAt(i) === ' ') i++; return s.charAt(i); };
    function factor() { const c = peek(); if (c === '-') { i++; return -factor(); } if (c === '+') { i++; return factor(); }
      if (c === '(') { i++; const v = expr(); if (peek() !== ')') throw new Error('bad'); i++; return v; }
      const m = /^(\d+\.?\d*|\.\d+)/.exec(s.slice(i)); if (!m) throw new Error('bad'); i += m[0].length; let v = parseFloat(m[0]); if (s.charAt(i) === '%') { i++; v = (base || 0) * v / 100; } return v; }
    function term() { let v = factor(); for (;;) { const c = peek(); if (c === '*') { i++; v *= factor(); } else if (c === '/') { i++; v /= factor(); } else return v; } }
    function expr() { let v = term(); for (;;) { const c = peek(); if (c === '+') { i++; v += term(); } else if (c === '-') { i++; v -= term(); } else return v; } }
    try { const v = expr(); if (peek() !== '' || !isFinite(v)) return null; return v; } catch (e) { return null; }
  }

  /* ---------------------------------------------------------------- shared state of the shell */
  const ui = {root: null, mounted: false, syncs: [], sig: '', raf: 0, leftTab: 'layers', rightTab: 'design', panels: {left: [], right: []}, hidden: false, ratio: false, corners: false, padEach: false, pageViews: {}};
  function refresh() { if (!ui.mounted || ui.raf) return; ui.raf = requestAnimationFrame(() => { ui.raf = 0; try { paintAll(); } catch (e) { if (window.console) console.error(e); } }); }
  function P(id, name) { return U().prop(id, name); }
  function sel() { return U().selIds(); }
  function same(a, b) { return a === b || (a !== null && b !== null && typeof a === 'object' && typeof b === 'object' && JSON.stringify(a) === JSON.stringify(b)); }
  function mixed(list, get) { let first, has = false; for (const id of list) { const v = typeof get === 'function' ? get(id) : P(id, get); if (!has) { first = v; has = true; } else if (!same(v, first)) return MIXED; } return first; }
  function write(label, fn, g) { if (!U().canEdit()) return; if (g) g.apply(fn); else HD.store.tx(label, fn); }
  function setAll(label, list, name, value, g) { write(label, () => { for (const id of list) if (HD.store.has(id)) HD.store.set(id, typeof name === 'string' ? {[name]: value} : name); }, g); }

  /* ---------------------------------------------------------------- controls */
  /* o: {label (text / icon name), title, get() -> number | MIXED | word, set(v, gesture), min, max, step, unit, dec, words:{auto:'auto'}, wide} */
  function numField(o) {
    const unit = o.unit || '', step = o.step || 1; let cur;
    const inp = h('input', {class: 'hd-in', type: 'text', 'aria-label': o.title, spellcheck: 'false', autocomplete: 'off'});
    const lab = h('span', {class: 'hd-flab', title: o.title + ' (drag to change)'}, o.icon ? icon(o.icon, 14) : o.label);
    const wrap = h('label', {class: 'hd-field' + (o.wide || (!o.icon && String(o.label || '').length > 2) ? ' wide' : ''), title: o.title}, lab, inp);
    const lim = v => { if (o.min !== undefined) v = Math.max(o.min, v); if (o.max !== undefined) v = Math.min(o.max, v); return v; };
    function show(force) { if (!force && document.activeElement === inp) return; cur = o.get(); const off = o.off && o.off(); inp.disabled = !!off || !U().canEdit();
      inp.value = cur === MIXED ? 'Mixed' : cur === null || cur === undefined ? '' : typeof cur === 'string' ? cur.charAt(0).toUpperCase() + cur.slice(1) : fmt(cur, o.dec) + unit; inp.classList.toggle('mixed', cur === MIXED); }
    function commit() { const txt = inp.value.trim(), low = txt.toLowerCase(); let v;
      if (o.words && o.words[low] !== undefined) v = o.words[low]; else { v = calc(txt, typeof cur === 'number' ? cur : 0, unit); if (v === null) { show(true); return; } v = lim(v); }
      if (v !== cur) o.set(v, null); show(true); }
    inp.addEventListener('focus', () => { setTimeout(() => { if (document.activeElement === inp) inp.select(); }, 0); });
    inp.addEventListener('blur', commit);
    inp.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); commit(); inp.select(); } else if (ev.key === 'Escape') { ev.preventDefault(); show(true); inp.blur(); if (T().canvas) T().canvas.focus({preventScroll: true}); }
      else if (ev.key === 'ArrowUp' || ev.key === 'ArrowDown') { ev.preventDefault(); const base = calc(inp.value, typeof cur === 'number' ? cur : 0, unit); const b = base === null ? (typeof cur === 'number' ? cur : 0) : base, v = lim(b + (ev.key === 'ArrowUp' ? 1 : -1) * step * (ev.shiftKey ? 10 : 1)); o.set(v, null); cur = v; inp.value = fmt(v, o.dec) + unit; inp.select(); } });
    let sx = 0, base = 0, g = null, moved = false;
    lab.addEventListener('pointerdown', ev => { if (ev.button || typeof cur !== 'number' || inp.disabled) return; ev.preventDefault(); sx = ev.clientX; base = cur; moved = false; g = new (U().Gesture)(o.title); try { lab.setPointerCapture(ev.pointerId); } catch (e) { /* synthetic */ }
      document.body.classList.add('hd-scrub');
      const mv = e2 => { const d = Math.round((e2.clientX - sx) / 2); if (!d && !moved) return; moved = true; const v = lim(Math.round((base + d * step * (e2.shiftKey ? 10 : 1)) / step) * step); o.set(v, g); cur = v; inp.value = fmt(v, o.dec) + unit; };
      const up = () => { lab.removeEventListener('pointermove', mv); lab.removeEventListener('pointerup', up); lab.removeEventListener('pointercancel', up); document.body.classList.remove('hd-scrub'); if (g) g.end(); g = null; if (!moved) inp.focus(); };
      lab.addEventListener('pointermove', mv); lab.addEventListener('pointerup', up); lab.addEventListener('pointercancel', up); });
    ui.syncs.push(show); show(true); wrap._show = show; return wrap;
  }
  /* opts: [{v, text | icon, title}] */
  function seg(opts, get, set, label) {
    const el = h('div', {class: 'hd-seg', role: 'radiogroup', 'aria-label': label});
    for (const op of opts) el.appendChild(h('button', {type: 'button', class: 'hd-segb', role: 'radio', title: op.title || op.text, 'aria-label': op.title || op.text, 'data-v': String(op.v), on: {click: () => { set(op.v); show(); }}}, op.icon ? icon(op.icon) : op.text));
    function show() { const v = get(); for (const b of el.children) { const on = v !== MIXED && String(v) === b.dataset.v; b.classList.toggle('on', on); b.setAttribute('aria-checked', String(on)); b.disabled = !U().canEdit(); } }
    ui.syncs.push(show); show(); return el;
  }
  function select(opts, get, set, label) {
    const el = h('select', {class: 'hd-sel', 'aria-label': label, title: label}); const mx = h('option', {value: '__mixed', text: 'Mixed', disabled: true, hidden: true}); el.appendChild(mx);
    for (const op of opts) el.appendChild(h('option', {value: String(op[0]), text: op[1]}));
    el.addEventListener('change', () => { const op = opts.find(x => String(x[0]) === el.value); if (op) set(op[0]); });
    function show() { if (document.activeElement === el) return; const v = get(); el.value = v === MIXED ? '__mixed' : String(v); if (el.selectedIndex < 0) el.value = '__mixed'; el.disabled = !U().canEdit(); }
    ui.syncs.push(show); show(); return el;
  }
  function toggle(ic, title, get, set, cls) { const b = ibtn(ic, title, () => { set(!(get() === true)); show(); }, cls); function show() { const v = get(); b.classList.toggle('on', v === true); b.setAttribute('aria-pressed', String(v === true)); b.disabled = !U().canEdit(); } ui.syncs.push(show); show(); return b; }
  function row() { const r = h('div', {class: 'hd-row'}); for (let i = 0; i < arguments.length; i++) add(r, arguments[i]); return r; }
  function section(parent, title, actions, o) {
    const head = h('div', {class: 'hd-shead'}, h('h3', {class: 'hd-stitle', text: title})), body = h('div', {class: 'hd-sbody'}), el = h('section', {class: 'hd-sec' + (o && o.cls ? ' ' + o.cls : ''), 'aria-label': title}, head, body);
    const acts = h('div', {class: 'hd-sacts'}); head.appendChild(acts); for (const a of (actions || [])) if (a) acts.appendChild(a.el || ibtn(a.icon, a.title, a.run));
    parent.appendChild(el); return {el: el, body: body, head: head, acts: acts};
  }

  /* ---------------------------------------------------------------- fonts */
  const FONTS = [
    ['Sans', 'Inter', '300;400;500;600;700'], ['Sans', 'Schibsted Grotesk', '400;500;600;700'], ['Sans', 'Roboto', '300;400;500;700'], ['Sans', 'Open Sans', '300;400;500;600;700'], ['Sans', 'Lato', '300;400;700'],
    ['Sans', 'Montserrat', '300;400;500;600;700'], ['Sans', 'Poppins', '300;400;500;600;700'], ['Sans', 'Nunito', '300;400;500;600;700'], ['Sans', 'Work Sans', '300;400;500;600;700'], ['Sans', 'DM Sans', '400;500;600;700'],
    ['Sans', 'Manrope', '400;500;600;700'], ['Sans', 'Plus Jakarta Sans', '400;500;600;700'], ['Sans', 'Outfit', '300;400;500;600;700'], ['Sans', 'Sora', '300;400;500;600;700'], ['Sans', 'Space Grotesk', '300;400;500;600;700'],
    ['Sans', 'Figtree', '300;400;500;600;700'], ['Sans', 'Urbanist', '300;400;500;600;700'], ['Sans', 'Lexend', '300;400;500;600;700'], ['Sans', 'Rubik', '300;400;500;600;700'], ['Sans', 'Raleway', '300;400;500;600;700'],
    ['Sans', 'Source Sans 3', '300;400;500;600;700'], ['Sans', 'IBM Plex Sans', '300;400;500;600;700'], ['Sans', 'Noto Sans', '300;400;500;600;700'], ['Sans', 'Mulish', '300;400;500;600;700'], ['Sans', 'Karla', '300;400;500;600;700'],
    ['Sans', 'Barlow', '300;400;500;600;700'], ['Sans', 'Oswald', '300;400;500;600;700'], ['Sans', 'Archivo', '300;400;500;600;700'], ['Sans', 'Quicksand', '300;400;500;600;700'], ['Sans', 'Bebas Neue', '400'],
    ['Serif', 'Literata', '300;400;500;600;700'], ['Serif', 'Playfair Display', '400;500;600;700'], ['Serif', 'Merriweather', '300;400;700'], ['Serif', 'Lora', '400;500;600;700'], ['Serif', 'Source Serif 4', '300;400;500;600;700'],
    ['Serif', 'DM Serif Display', '400'], ['Serif', 'Libre Baskerville', '400;700'], ['Serif', 'Cormorant Garamond', '300;400;500;600;700'], ['Serif', 'Fraunces', '300;400;500;600;700'], ['Serif', 'EB Garamond', '400;500;600;700'], ['Serif', 'Crimson Pro', '300;400;500;600;700'],
    ['Mono', 'JetBrains Mono', '300;400;500;600;700'], ['Mono', 'IBM Plex Mono', '300;400;500;600;700'], ['Mono', 'Space Mono', '400;700'], ['Mono', 'Fira Code', '300;400;500;600;700'], ['Mono', 'Roboto Mono', '300;400;500;600;700'],
    ['Display', 'Pacifico', '400'], ['Display', 'Caveat', '400;500;600;700'], ['Display', 'Dancing Script', '400;500;600;700'], ['Display', 'Lobster', '400'], ['Display', 'Permanent Marker', '400'], ['Display', 'Abril Fatface', '400'], ['Display', 'Righteous', '400'], ['Display', 'Comfortaa', '300;400;500;600;700'],
    ['Indian languages', 'Noto Sans Devanagari', '300;400;500;600;700'], ['Indian languages', 'Noto Serif Devanagari', '300;400;500;600;700'], ['Indian languages', 'Hind', '300;400;500;600;700'], ['Indian languages', 'Mukta', '300;400;500;600;700'],
    ['Indian languages', 'Baloo 2', '400;500;600;700'], ['Indian languages', 'Anek Devanagari', '300;400;500;600;700'], ['Indian languages', 'Tiro Devanagari Hindi', '400'], ['Indian languages', 'Kalam', '300;400;700'], ['Indian languages', 'Rajdhani', '300;400;500;600;700'], ['Indian languages', 'Yatra One', '400'],
    ['Indian languages', 'Noto Sans Tamil', '300;400;500;600;700'], ['Indian languages', 'Hind Madurai', '300;400;500;600;700'], ['Indian languages', 'Noto Sans Telugu', '300;400;500;600;700'], ['Indian languages', 'Noto Sans Bengali', '300;400;500;600;700'], ['Indian languages', 'Hind Siliguri', '300;400;500;600;700'],
    ['Indian languages', 'Noto Sans Gujarati', '300;400;500;600;700'], ['Indian languages', 'Noto Sans Kannada', '300;400;500;600;700'], ['Indian languages', 'Noto Sans Malayalam', '300;400;500;600;700'], ['Indian languages', 'Noto Sans Gurmukhi', '300;400;500;600;700'], ['Indian languages', 'Noto Nastaliq Urdu', '400;500;600;700']
  ];
  const fontState = {};
  function fontInfo(family) { return FONTS.find(f => f[1].toLowerCase() === String(family).toLowerCase()); }
  function fontWeights(family) { const f = fontInfo(family); return f ? f[2].split(';').map(Number) : [400, 700]; }
  function loadFont(family) {
    family = String(family || ''); if (HD.render && HD.render.loadFont) { if (!fontState[family]) fontState[family] = HD.render.loadFont(family, 400); return fontState[family]; }
    const f = fontInfo(family); if (!f) return Promise.resolve(false); if (fontState[f[1]]) return fontState[f[1]];
    const href = 'https://fonts.googleapis.com/css2?family=' + encodeURIComponent(f[1]).replace(/%20/g, '+') + ':wght@' + f[2] + '&display=swap';
    if (!document.querySelector('link[data-hd-font="' + f[1] + '"]')) document.head.appendChild(h('link', {rel: 'stylesheet', href: href, 'data-hd-font': f[1]}));
    fontState[f[1]] = new Promise(resolve => { const done = ok => resolve(ok); if (!document.fonts || !document.fonts.load) { setTimeout(() => done(true), 800); return; }
      const tryLoad = n => { document.fonts.load('400 16px "' + f[1] + '"', 'Aa\u0905').then(r => { if (r && r.length) done(true); else if (n > 0) setTimeout(() => tryLoad(n - 1), 250); else done(false); }).catch(() => done(false)); }; tryLoad(16); });
    fontState[f[1]].then(ok => { if (ok) fontReady(f[1]); });
    return fontState[f[1]];
  }
  function fontReady(family) {
    if (!ui.mounted || !HD.store || !HD.sel.page) return; if (HD.render && HD.render.fontLoaded) { HD.render.fontLoaded(family); return; }
    if (HD.render && HD.render.invalidate) HD.render.invalidate(); if (T().text && T().text.el) { T().text.style(); T().text.place(); }
  }
  function fontPicker(anchor, current, choose) {
    const q = h('input', {class: 'hd-in hd-search', type: 'search', placeholder: 'Search fonts', 'aria-label': 'Search fonts', autofocus: true}), list = h('div', {class: 'hd-fontlist', role: 'listbox', 'aria-label': 'Fonts'});
    function draw() { clear(list); const s = q.value.trim().toLowerCase(); let group = '';
      for (const f of FONTS) { if (s && f[1].toLowerCase().indexOf(s) < 0 && f[0].toLowerCase().indexOf(s) < 0) continue; if (f[0] !== group) { group = f[0]; list.appendChild(h('div', {class: 'hd-mhead', text: group})); }
        list.appendChild(h('button', {class: 'hd-mi' + (f[1] === current ? ' cur' : ''), type: 'button', role: 'option', 'aria-selected': String(f[1] === current), on: {click: () => { handle.close(); choose(f[1]); }}}, h('span', {class: 'hd-mic'}, f[1] === current ? icon('check') : null), h('span', {class: 'hd-mlab', text: f[1]}))); }
      if (!list.firstChild) list.appendChild(h('div', {class: 'hd-none pad', text: 'No font with that name.'})); }
    q.addEventListener('input', draw); q.addEventListener('keydown', ev => { if (ev.key === 'ArrowDown') { ev.preventDefault(); const b = list.querySelector('.hd-mi'); if (b) b.focus(); } else if (ev.key === 'Enter') { const b = list.querySelector('.hd-mi'); if (b) b.click(); } });
    list.addEventListener('keydown', ev => { const bs = Array.from(list.querySelectorAll('.hd-mi')), i = bs.indexOf(document.activeElement); if (ev.key === 'ArrowDown' && bs[i + 1]) { ev.preventDefault(); bs[i + 1].focus(); } else if (ev.key === 'ArrowUp') { ev.preventDefault(); (bs[i - 1] || q).focus(); } });
    draw(); const handle = pop(anchor, h('div', {class: 'hd-fontpick'}, q, list), {cls: 'hd-pop-font', label: 'Font', side: 'left'}); const curEl = list.querySelector('.cur'); if (curEl) curEl.scrollIntoView({block: 'center'}); return handle;
  }
  const WEIGHT_NAME = {100: 'Thin', 200: 'Extra light', 300: 'Light', 400: 'Regular', 500: 'Medium', 600: 'Semi bold', 700: 'Bold', 800: 'Extra bold', 900: 'Black'};

  /* ---------------------------------------------------------------- top bar */
  const SHAPES = [['rect', 'rect', 'Rectangle', 'r'], ['ellipse', 'ellipse', 'Ellipse', 'o'], ['line', 'line', 'Line', 'l'], ['polygon', 'polygon', 'Polygon', ''], ['star', 'star', 'Star', '']];
  const DRAWS = [['pen', 'pen', 'Pen', 'p'], ['pencil', 'pencil', 'Pencil', 'shift+p']];
  const PRESETS = [
    {head: 'Phone'}, ['Phone', 390, 844], ['Android', 360, 800], ['Small phone', 320, 568],
    {head: 'Tablet and desktop'}, ['Tablet', 834, 1194], ['Desktop', 1440, 1024], ['Laptop', 1280, 832], ['Presentation', 1920, 1080],
    {head: 'Paper'}, ['A4', 595, 842], ['A5', 420, 595], ['Visiting card', 1050, 600],
    {head: 'Social'}, ['Square post', 1080, 1080], ['Portrait post', 1080, 1350], ['Story or status', 1080, 1920], ['Video thumbnail', 1280, 720], ['Link preview', 1200, 630]
  ];
  const top = {};
  function toolBtn(id, ic, title, keys) { const b = h('button', {class: 'hd-tool', type: 'button', 'data-tool': id, title: title + (keys ? '  (' + keysLabel(keys) + ')' : ''), 'aria-label': title, 'aria-pressed': 'false'}, icon(ic, 18)); b.addEventListener('click', () => T().set(id)); return b; }
  function toolGroup(list, key, label) {
    const cur = () => list.find(x => x[0] === ui[key]) || list[0]; let main = null;
    const wrap = h('div', {class: 'hd-toolg'}), caret = h('button', {class: 'hd-tcaret', type: 'button', title: label, 'aria-label': label, 'aria-haspopup': 'menu'}, icon('down', 10));
    function draw() { const c = cur(), nb = toolBtn(c[0], c[1], c[2], c[3]); if (main) wrap.replaceChild(nb, main); else wrap.insertBefore(nb, wrap.firstChild); main = nb; }
    caret.addEventListener('click', () => menu(wrap, list.map(x => ({label: x[2], icon: x[1], keys: x[3], checked: T().current === x[0] ? true : undefined, run: () => { ui[key] = x[0]; draw(); T().set(x[0]); syncTools(); }})), {label: label}));
    wrap.appendChild(caret); draw(); wrap._draw = draw; wrap._list = list; wrap._key = key; return wrap;
  }
  function presetMenu(anchor) {
    menu(anchor, PRESETS.map(p => p.head ? {head: p.head} : {label: p[0], hint: p[1] + ' × ' + p[2], run: () => A().addFrame(p[1], p[2], p[0])}), {label: 'Frame sizes'});
  }
  function buildTop() {
    const f = (HD.app && HD.app.file) || {name: 'Untitled'};
    top.name = h('button', {class: 'hd-fname', type: 'button', title: 'Rename this file'}, h('span', {class: 'hd-fname-t', text: f.name || 'Untitled'}));
    top.name.addEventListener('click', renameFile);
    top.role = h('span', {class: 'hd-chip', hidden: true, text: 'View only'});
    const left = h('div', {class: 'hd-top-l'}, ibtn('back', 'Back to your files', () => { location.hash = '#/'; }), ibtn('menu', 'Main menu', ev => mainMenu(ev.currentTarget)), h('div', {class: 'hd-vsep'}), top.name, top.role);
    ui.shapeTool = ui.shapeTool || 'rect'; ui.drawTool = ui.drawTool || 'pen';
    const frameG = h('div', {class: 'hd-toolg'}, toolBtn('frame', 'frame', 'Frame', 'f'), h('button', {class: 'hd-tcaret', type: 'button', title: 'Frame sizes', 'aria-label': 'Frame sizes', 'aria-haspopup': 'menu', on: {click: ev => presetMenu(ev.currentTarget.parentNode)}}, icon('down', 10)));
    top.shape = toolGroup(SHAPES, 'shapeTool', 'Shape tools'); top.draw = toolGroup(DRAWS, 'drawTool', 'Drawing tools');
    top.tools = h('div', {class: 'hd-toolbar', role: 'toolbar', 'aria-label': 'Tools'}, toolBtn('move', 'move', 'Move', 'v'), frameG, top.shape, top.draw, toolBtn('text', 'text', 'Text', 't'), toolBtn('hand', 'hand', 'Hand', 'h'), toolBtn('comment', 'comment', 'Comment', 'c'));
    top.status = h('span', {class: 'hd-status', role: 'status', 'aria-live': 'polite'}, h('i', {class: 'hd-dot'}), h('span', {text: 'Connecting'}));
    top.people = h('div', {class: 'hd-people', 'aria-label': 'People in this file'});
    top.undo = ibtn('undo', 'Undo  (' + keysLabel('mod+z') + ')', () => A().undo()); top.redo = ibtn('redo', 'Redo  (' + keysLabel('mod+shift+z') + ')', () => A().redo());
    top.zoom = h('button', {class: 'hd-zoom', type: 'button', title: 'Zoom and view', 'aria-haspopup': 'menu'}, h('span', {text: '100%'}), icon('down', 10)); top.zoom.addEventListener('click', () => zoomMenu(top.zoom));
    top.share = h('button', {class: 'hd-btn', type: 'button', title: 'Share this file', on: {click: () => fire('share', HD.app.file)}}, icon('share'), h('span', {class: 'hd-btn-t', text: 'Share'}));
    top.export = h('button', {class: 'hd-btn', type: 'button', title: 'Export  (' + keysLabel('mod+shift+e') + ')', on: {click: () => fire('export', sel())}}, icon('export'), h('span', {class: 'hd-btn-t', text: 'Export'}));
    top.present = h('button', {class: 'hd-btn pri', type: 'button', title: 'Present', 'aria-label': 'Present', on: {click: () => fire('present', presentStart())}}, icon('play'));
    const right = h('div', {class: 'hd-top-r'}, top.status, top.people, h('div', {class: 'hd-vsep'}), top.undo, top.redo, top.zoom, h('div', {class: 'hd-vsep'}), top.share, top.export, top.present);
    return h('header', {class: 'hd-top'}, left, top.tools, right);
  }
  function presentStart() { const s = sel(); for (const id of s) { const c = U().chain(id); if (c.length && U().typeOf(c[0]) === 'FRAME') return c[0]; } const k = HD.store.children(HD.sel.page).find(id => U().typeOf(id) === 'FRAME'); return k || null; }
  function syncTools() {
    if (!top.tools) return; const cur = T().current;
    for (const g of [top.shape, top.draw]) { if (g._list.some(x => x[0] === cur) && ui[g._key] !== cur) { ui[g._key] = cur; g._draw(); } }
    const edit = U().canEdit();
    for (const b of top.tools.querySelectorAll('.hd-tool')) { const on = b.dataset.tool === cur; b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); b.disabled = !edit && !{move: 1, hand: 1, comment: 1}[b.dataset.tool]; }
    for (const b of top.tools.querySelectorAll('.hd-tcaret')) b.disabled = !edit;
  }
  function syncTop() {
    if (!top.name) return; const f = (HD.app && HD.app.file) || {}; const t = top.name.firstChild; if (t && t.tagName === 'SPAN' && t.textContent !== (f.name || 'Untitled')) t.textContent = f.name || 'Untitled';
    const edit = U().canEdit(); top.role.hidden = edit; top.undo.disabled = !edit || !HD.store.canUndo(); top.redo.disabled = !edit || !HD.store.canRedo(); syncTools(); syncZoom(); syncNet();
  }
  let zoomShown = 0;
  function syncZoom() { const z = (HD.render.view && HD.render.view.zoom) || 1; if (Math.abs(z - zoomShown) < 0.0005 || !top.zoom) return; zoomShown = z; top.zoom.firstChild.textContent = Math.round(z * 100) + '%'; }
  let peopleSig = '';
  function syncNet() {
    if (!top.status) return; const st = (HD.net && HD.net.status) || 'offline', busy = st === 'live' && HD.net.pending && HD.net.pending() > 0, lab = st === 'live' ? (busy ? 'Saving\u2026' : 'Saved') : st === 'connecting' ? 'Connecting' : 'Offline';
    top.status.className = 'hd-status ' + st; top.status.lastChild.textContent = lab; top.status.title = st === 'live' ? 'Every change is saved as you make it.' : st === 'connecting' ? 'Connecting to the server…' : 'No connection. Your changes are kept here and sent when you are back online.';
    const users = [], me = HD.net && HD.net.cid; if (HD.net && HD.net.users && HD.net.users.forEach) HD.net.users.forEach((u, cid) => { if (u && cid !== me && u.cid !== me) users.push({cid: cid, name: String(u.name || 'Guest'), color: u.color || '#EE8F35', u: u}); });
    const sig = users.map(u => u.cid + u.name + u.color).join('|'); if (sig === peopleSig) return; peopleSig = sig; clear(top.people);
    users.slice(0, 4).forEach(u => { const b = h('button', {class: 'hd-person', type: 'button', title: u.name + ' (click to go to their cursor)', 'aria-label': u.name, style: {backgroundColor: u.color}, text: u.name.trim().charAt(0).toUpperCase() || '?'});
      b.addEventListener('click', () => { const x = HD.net.users.get(u.cid); if (!x || typeof x.x !== 'number') return; if (x.page && x.page !== HD.sel.page && HD.store.has(x.page)) setPage(x.page); const c = T().view.centre(); HD.render.setView(T().view.at((HD.render.view.zoom || 1), x.x, x.y, c[0], c[1]), true); });
      top.people.appendChild(b); });
    if (users.length > 4) top.people.appendChild(h('span', {class: 'hd-person more', text: '+' + (users.length - 4), title: users.slice(4).map(u => u.name).join(', ')}));
  }
  function renameFile() {
    const f = HD.app && HD.app.file; if (!f || !U().canEdit()) return; const inp = h('input', {class: 'hd-in hd-fname-in', type: 'text', value: f.name || '', 'aria-label': 'File name', maxlength: '120'}); let done = false;
    const finish = save => { if (done) return; done = true; const v = inp.value.trim(); clear(top.name); top.name.appendChild(h('span', {class: 'hd-fname-t', text: f.name || 'Untitled'}));
      if (save && v && v !== f.name) { const old = f.name; f.name = v; syncTop(); api('PATCH', '/files/' + encodeURIComponent(f.id), {name: v}).catch(e => { f.name = old; syncTop(); toast(e.message || 'The name could not be saved.', true); }); } };
    inp.addEventListener('keydown', ev => { ev.stopPropagation(); if (ev.key === 'Enter') finish(true); else if (ev.key === 'Escape') finish(false); }); inp.addEventListener('blur', () => finish(true)); inp.addEventListener('click', ev => ev.stopPropagation());
    clear(top.name); top.name.appendChild(inp); inp.focus(); inp.select();
  }
  function themeItems() { const th = window.HoolaTheme, cur = th ? th.theme() : 'system'; return [['light', 'Light', 'sun'], ['dark', 'Dark', 'moon'], ['system', 'Match the computer', 'sidebar']].map(t => ({label: t[1], icon: t[2], checked: cur === t[0] ? true : undefined, run: () => { if (th) th.setTheme(t[0]); HD.render.invalidate(); }})); }
  function mainMenu(anchor) {
    menu(anchor, [{label: 'Back to your files', icon: 'home', run: () => { location.hash = '#/'; }}, {label: 'Open the Console', icon: 'link', run: () => { location.href = '/console/'; }}, '-',
      {label: 'Find a command…', icon: 'search', keys: 'mod+k', run: palette}, {label: 'Keyboard shortcuts', icon: 'keys', keys: 'shift+/', run: shortcutSheet}, {label: ui.hidden ? 'Show the panels' : 'Hide the panels', icon: 'sidebar', keys: 'mod+\\', run: toggleUI},
      {label: 'Version history', icon: 'history', run: () => fire('versions', HD.app.file)}, {label: 'Ask Hoola to design…', icon: 'spark', run: () => runCmd('ai')}, '-', {head: 'Appearance'}].concat(themeItems()).concat((menus.main || []).length ? ['-'] : []).concat(menus.main || []), {label: 'Main menu'});
  }
  function zoomMenu(anchor) {
    const z = Math.round(((HD.render.view && HD.render.view.zoom) || 1) * 100);
    menu(anchor, [{label: 'Zoom in', keys: '+', run: () => T().view.zoomBy(1.5)}, {label: 'Zoom out', keys: '-', run: () => T().view.zoomBy(1 / 1.5)}, {label: 'Zoom to fit', keys: 'shift+1', run: () => T().view.fit()}, {label: 'Zoom to selection', keys: 'shift+2', disabled: !sel().length, run: () => A().zoomSelection()}, '-',
      {label: '50%', checked: z === 50 ? true : undefined, run: () => T().view.zoomTo(0.5, true)}, {label: '100%', keys: '0', checked: z === 100 ? true : undefined, run: () => T().view.zoomTo(1, true)}, {label: '200%', checked: z === 200 ? true : undefined, run: () => T().view.zoomTo(2, true)}, '-',
      {label: 'Snap to other layers', checked: T().snapOn ? true : undefined, run: () => { T().snapOn = !T().snapOn; }}, {label: ui.hidden ? 'Show the panels' : 'Hide the panels', keys: 'mod+\\', run: toggleUI}].concat(menus.view || []), {label: 'Zoom'});
  }
  function toggleUI() { ui.hidden = !ui.hidden; if (ui.root) ui.root.classList.toggle('hd-noui', ui.hidden); setTimeout(() => { if (HD.render.resize) HD.render.resize(); HD.render.invalidate(); }, 0); }

  /* ---------------------------------------------------------------- pages */
  function setPage(id) {
    if (!HD.store.has(id) || id === HD.sel.page) return; const v = HD.render.view; if (v && HD.sel.page) ui.pageViews[HD.sel.page] = {x: v.x, y: v.y, zoom: v.zoom};
    if (T().text && T().text.el) T().text.commit(); HD.sel.clear(); HD.sel.setPage(id); T().state.scope = null; L.dirty = true; if (L.scroll) L.scroll.scrollTop = 0;
    const pv = ui.pageViews[id]; if (pv) HD.render.setView(pv); else HD.render.zoomToFit(undefined, false); HD.render.invalidate(); refresh();
  }
  function addPage() { if (!U().canEdit()) return; let id = null, n = HD.store.pages().length + 1; const names = new Set(HD.store.pages().map(p => (HD.store.get(p) || {}).name)); while (names.has('Page ' + n)) n++;
    HD.store.tx('Add page', () => { id = HD.store.create('PAGE', HD.store.ROOT, {name: 'Page ' + n}); }); if (id) { ui.pageViews[id] = {x: 0, y: 0, zoom: 1}; setPage(id); } }
  function deletePage(id) { const pages = HD.store.pages(); if (pages.length < 2) { toast('A file needs at least one page.'); return; } if (!U().canEdit()) return;
    const other = pages[pages.indexOf(id) === 0 ? 1 : pages.indexOf(id) - 1]; if (id === HD.sel.page) setPage(other); HD.store.tx('Delete page', () => HD.store.remove([id])); refresh(); }
  function inlineEdit(host, value, done, label) {
    const inp = h('input', {class: 'hd-in hd-inline', type: 'text', value: value, 'aria-label': label || 'Name', maxlength: '200'}); let fin = false; const old = Array.from(host.childNodes);
    const finish = save => { if (fin) return; fin = true; const v = inp.value.trim(); if (inp.parentNode === host) host.removeChild(inp); for (const o of old) host.appendChild(o); done(save && v ? v : null); };
    inp.addEventListener('keydown', ev => { ev.stopPropagation(); if (ev.key === 'Enter') { ev.preventDefault(); finish(true); } else if (ev.key === 'Escape') { ev.preventDefault(); finish(false); } });
    inp.addEventListener('blur', () => finish(true)); for (const t of ['pointerdown', 'click', 'dblclick']) inp.addEventListener(t, ev => ev.stopPropagation());
    clear(host); host.appendChild(inp); inp.focus(); inp.select(); return inp;
  }
  const Pg = {el: null, list: null, open: true, sig: '', editing: null};
  function pagesBuild() {
    Pg.list = h('div', {class: 'hd-pages', role: 'listbox', 'aria-label': 'Pages'});
    Pg.caret = h('button', {class: 'hd-ib sm', type: 'button', title: 'Show or hide the pages', 'aria-label': 'Show or hide the pages', 'aria-expanded': 'true'}, icon('down', 12));
    Pg.caret.addEventListener('click', () => { Pg.open = !Pg.open; Pg.list.hidden = !Pg.open; Pg.caret.classList.toggle('shut', !Pg.open); Pg.caret.setAttribute('aria-expanded', String(Pg.open)); });
    Pg.addBtn = ibtn('plus', 'Add a page', addPage, 'sm');
    Pg.el = h('div', {class: 'hd-pagesec'}, h('div', {class: 'hd-shead'}, Pg.caret, h('h3', {class: 'hd-stitle', text: 'Pages'}), h('div', {class: 'hd-sacts'}, Pg.addBtn)), Pg.list);
    return Pg.el;
  }
  function pagesPaint() {
    if (!Pg.list || Pg.editing) return; const pages = HD.store.pages(), sig = pages.map(p => p + ':' + ((HD.store.get(p) || {}).name || '')).join('|') + '#' + HD.sel.page + U().canEdit(); if (sig === Pg.sig) return; Pg.sig = sig; clear(Pg.list); Pg.addBtn.disabled = !U().canEdit();
    pages.forEach(id => { const n = HD.store.get(id) || {}, cur = id === HD.sel.page;
      const b = h('div', {class: 'hd-page' + (cur ? ' cur' : ''), role: 'option', 'aria-selected': String(cur), tabIndex: 0, 'data-id': id}, h('span', {class: 'hd-page-ic'}, cur ? icon('check', 12) : null), h('span', {class: 'hd-lname', text: n.name || 'Page'}));
      const ren = () => { if (!U().canEdit()) return; Pg.editing = id; inlineEdit(b.lastChild, n.name || '', v => { Pg.editing = null; if (v) A().rename(id, v); Pg.sig = ''; refresh(); }, 'Page name'); };
      b.addEventListener('click', () => setPage(id)); b.addEventListener('dblclick', ren);
      b.addEventListener('keydown', ev => { if (ev.target !== b) return; if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); setPage(id); } else if (ev.key === 'F2') ren(); });
      b.addEventListener('contextmenu', ev => { ev.preventDefault(); const i = pages.indexOf(id); menu({x: ev.clientX, y: ev.clientY}, [{label: 'Rename', run: ren, disabled: !U().canEdit()},
        {label: 'Move up', disabled: !U().canEdit() || i === 0, run: () => { HD.store.tx('Reorder pages', () => HD.store.move([id], HD.store.ROOT, pages[i - 1])); }},
        {label: 'Move down', disabled: !U().canEdit() || i === pages.length - 1, run: () => { HD.store.tx('Reorder pages', () => HD.store.move([id], HD.store.ROOT, pages[i + 2] || null)); }}, '-',
        {label: 'Delete page', danger: true, disabled: !U().canEdit() || pages.length < 2, run: () => deletePage(id)}], {label: 'Page'}); });
      pageDrag(b, id); Pg.list.appendChild(b); });
  }
  function pageDrag(b, id) {
    b.addEventListener('pointerdown', ev => { if (ev.button || !U().canEdit() || ev.target.tagName === 'INPUT') return; const y0 = ev.clientY; let on = false, before;
      const mv = e2 => { if (!on && Math.abs(e2.clientY - y0) < 5) return; on = true; b.classList.add('drag'); const els = Array.from(Pg.list.children); before = null; for (const el of els) el.classList.remove('dropb', 'dropa');
        for (const el of els) { const r = el.getBoundingClientRect(); if (e2.clientY < r.top + r.height / 2) { before = el.dataset.id; el.classList.add('dropb'); break; } } if (before === null && els.length) els[els.length - 1].classList.add('dropa'); };
      const up = () => { window.removeEventListener('pointermove', mv); window.removeEventListener('pointerup', up); b.classList.remove('drag'); for (const el of Pg.list.children) el.classList.remove('dropb', 'dropa');
        if (on && before !== id) { const pages = HD.store.pages(); if (pages[pages.indexOf(id) + 1] !== before && !(before === null && pages[pages.length - 1] === id)) HD.store.tx('Reorder pages', () => HD.store.move([id], HD.store.ROOT, before)); Pg.sig = ''; refresh(); } };
      window.addEventListener('pointermove', mv); window.addEventListener('pointerup', up); });
  }

  /* ---------------------------------------------------------------- layers (only the rows on screen exist in the DOM) */
  const HOLDS = {FRAME: 1, GROUP: 1, SECTION: 1, COMPONENT: 1, COMPONENT_SET: 1, INSTANCE: 1};
  const L = {rows: [], index: new Map(), cache: new Map(), expanded: new Set(), H: 28, anchor: null, editing: null, dirty: true, scroll: null, inner: null, fromPanel: false, selSig: '', count: null};
  function flatten() {
    const rows = [], idx = new Map(), st = HD.store;
    const walk = (pid, depth) => { const kids = st.children(pid); for (let i = kids.length - 1; i >= 0; i--) { const k = kids[i], n = st.get(k); if (!n) continue; const has = !!HOLDS[n.type] && st.children(k).length > 0, open = has && L.expanded.has(k);
      idx.set(k, rows.length); rows.push({id: k, depth: depth, has: has, open: open}); if (open) walk(k, depth + 1); } };
    if (HD.sel.page && st.has(HD.sel.page)) walk(HD.sel.page, 0);
    L.rows = rows; L.index = idx; L.dirty = false;
  }
  function layersBuild() {
    L.inner = h('div', {class: 'hd-linner'}); L.ind = h('div', {class: 'hd-lind', hidden: true}); L.cache = new Map();
    L.scroll = h('div', {class: 'hd-lscroll', role: 'tree', 'aria-label': 'Layers', 'aria-multiselectable': 'true', tabIndex: 0}, L.inner);
    L.empty = h('div', {class: 'hd-lempty', hidden: true}, h('p', {text: 'This page is empty.'}), h('p', {class: 'hd-dimtext', text: 'Pick Frame (F) or a shape and drag on the canvas.'}));
    L.count = h('span', {class: 'hd-count'});
    let raf = 0; L.scroll.addEventListener('scroll', () => { if (raf) return; raf = requestAnimationFrame(() => { raf = 0; layersPaint(); }); }, {passive: true});
    L.inner.addEventListener('pointerdown', rowDown); L.inner.addEventListener('click', rowClick); L.inner.addEventListener('dblclick', rowDbl);
    L.inner.addEventListener('contextmenu', ev => { const r = rowOf(ev); ev.preventDefault(); if (r && !HD.sel.has(r.id)) { L.fromPanel = true; HD.sel.set([r.id]); } contextMenu(ev.clientX, ev.clientY, null); });
    L.inner.addEventListener('pointermove', ev => { const r = rowOf(ev), id = r && !HD.sel.has(r.id) ? r.id : null; if (T().state.hover !== id && !L.drag) { T().state.hover = id; T().redraw(); } });
    L.inner.addEventListener('pointerleave', () => { if (T().state.hover) { T().state.hover = null; T().redraw(); } });
    L.scroll.addEventListener('keydown', layersKey);
    if (window.ResizeObserver) new ResizeObserver(() => layersPaint()).observe(L.scroll);
    return h('div', {class: 'hd-layersec'}, h('div', {class: 'hd-shead'}, h('h3', {class: 'hd-stitle', text: 'Layers'}), L.count), L.scroll, L.empty);
  }
  function rowOf(ev) { const el = ev.target && ev.target.closest ? ev.target.closest('.hd-lrow') : null; if (!el) return null; const i = L.index.get(el.dataset.id); return i === undefined ? null : L.rows[i]; }
  function layersPaint() {
    if (!L.scroll || L.editing) return; if (L.dirty) flatten();
    const rows = L.rows, H = L.H, topPx = L.scroll.scrollTop, hh = L.scroll.clientHeight || 400, a = Math.max(0, Math.floor(topPx / H) - 6), b = Math.min(rows.length, Math.ceil((topPx + hh) / H) + 6);
    L.inner.style.height = (rows.length * H) + 'px'; L.empty.hidden = rows.length > 0; L.scroll.hidden = rows.length === 0; L.count.textContent = rows.length > 200 ? String(rows.length) : '';
    const edit = U().canEdit(), selSet = new Set(HD.sel.ids || []), next = new Map(), order = []; let same = true;
    for (let i = a; i < b; i++) { const r = rows[i], n = HD.store.get(r.id); if (!n) continue; const isSel = selSet.has(r.id); let inSel = false;
      if (!isSel && selSet.size && r.depth) { let c = HD.store.parent(r.id), g = 0; while (c && g++ < 60) { if (selSet.has(c)) { inSel = true; break; } c = HD.store.parent(c); } }
      const hidden = n.visible === false, locked = n.locked === true, img = n.type === 'RECT' && Array.isArray(n.fills) && n.fills.some(f => f && f.type === 'image');
      const key = [i, r.depth, r.has ? 1 : 0, r.open ? 1 : 0, isSel ? 1 : 0, inSel ? 1 : 0, hidden ? 1 : 0, locked ? 1 : 0, img ? 1 : 0, edit ? 1 : 0, n.type, n.name, n.mask === true ? 1 : 0, n.bool || ''].join('\u0001'), old = L.cache.get(r.id);
      if (old && old.key === key) { next.set(r.id, old); order.push(old.el); continue; } same = false;
      const el = h('div', {class: 'hd-lrow' + (isSel ? ' sel' : inSel ? ' insel' : '') + (hidden ? ' off' : '') + (n.type === 'COMPONENT' || n.type === 'INSTANCE' || n.type === 'COMPONENT_SET' ? ' comp' : '') + (n.mask === true ? ' mask' : '') + (n.type === 'GROUP' && n.bool ? ' bool' : ''), role: 'treeitem', 'data-bool': n.type === 'GROUP' && n.bool ? String(n.bool) : null, 'aria-selected': String(isSel), 'aria-level': String(r.depth + 1), 'aria-expanded': r.has ? String(r.open) : null, 'data-id': r.id, style: {top: (i * H) + 'px', paddingLeft: (6 + r.depth * 14) + 'px'}},
        r.has ? h('button', {class: 'hd-lcaret' + (r.open ? ' open' : ''), type: 'button', tabIndex: -1, 'aria-label': r.open ? 'Collapse' : 'Expand'}, icon('right', 10)) : h('span', {class: 'hd-lcaret none'}),
        h('span', {class: 'hd-ltype', title: 'Double-click to zoom to this layer'}, icon(img ? 'image' : TYPE_ICON[n.type] || 'rect', 14)),
        h('span', {class: 'hd-lname', text: n.name || n.type}),
        edit ? h('button', {class: 'hd-lbtn hd-llock' + (locked ? ' on' : ''), type: 'button', tabIndex: -1, title: locked ? 'Unlock' : 'Lock', 'aria-label': locked ? 'Unlock' : 'Lock', 'aria-pressed': String(locked)}, icon(locked ? 'lock' : 'unlock', 14)) : null,
        edit ? h('button', {class: 'hd-lbtn hd-leye' + (hidden ? ' on' : ''), type: 'button', tabIndex: -1, title: hidden ? 'Show' : 'Hide', 'aria-label': hidden ? 'Show' : 'Hide', 'aria-pressed': String(hidden)}, icon(hidden ? 'eyeoff' : 'eye', 14)) : null);
      next.set(r.id, {key: key, el: el}); order.push(el); }
    if (same && next.size === L.cache.size && L.ind.parentNode === L.inner) return;   /* nothing on screen changed: the rows (and a click in progress) stay as they are */
    L.cache.forEach((v, id) => { const keep = next.get(id); if ((!keep || keep.el !== v.el) && v.el.parentNode === L.inner) L.inner.removeChild(v.el); });
    let ref = L.inner.firstChild; for (const el of order) { if (el === ref) { ref = ref.nextSibling; continue; } L.inner.insertBefore(el, ref); }
    L.cache = next; if (L.ind.parentNode !== L.inner) L.inner.appendChild(L.ind);
  }
  function reveal(ids) {
    let changed = false; for (const id of ids) { let c = HD.store.parent(id), g = 0; while (c && g++ < 200 && !U().pageLike(c)) { if (!L.expanded.has(c)) { L.expanded.add(c); changed = true; } c = HD.store.parent(c); } }
    if (changed || L.dirty) flatten(); const i = L.index.get(ids[0]); if (i === undefined || !L.scroll) return; const y = i * L.H, hh = L.scroll.clientHeight; if (y < L.scroll.scrollTop || y + L.H > L.scroll.scrollTop + hh) L.scroll.scrollTop = Math.max(0, y - hh / 2);
  }
  function rowClick(ev) {
    const r = rowOf(ev); if (!r) return; const btn = ev.target.closest('button'); if (!btn) return;
    if (btn.classList.contains('hd-lcaret')) { if (L.expanded.has(r.id)) L.expanded.delete(r.id); else L.expanded.add(r.id); L.dirty = true; layersPaint(); return; }
    const name = btn.classList.contains('hd-leye') ? 'visible' : 'locked', list = HD.sel.has(r.id) ? sel() : [r.id], curV = name === 'visible' ? P(r.id, 'visible') !== false : P(r.id, 'locked') === true;
    setAll(name === 'visible' ? 'Show / hide' : 'Lock / unlock', list, name, !curV);
  }
  function rowDbl(ev) { const r = rowOf(ev); if (!r || ev.target.closest('button')) return; if (ev.target.closest('.hd-ltype')) { T().view.fit([r.id]); return; } renameLayer(r.id); }
  function renameLayer(id) {
    if (!U().canEdit() || !HD.store.has(id)) return; reveal([id]); layersPaint(); const el = L.inner.querySelector('.hd-lrow[data-id="' + String(id).replace(/"/g, '') + '"] .hd-lname'); if (!el) return;
    L.editing = id; inlineEdit(el, (HD.store.get(id) || {}).name || '', v => { L.editing = null; if (v) A().rename(id, v); layersPaint(); if (L.scroll) L.scroll.focus({preventScroll: true}); }, 'Layer name');
  }
  function rowDown(ev) {
    const r = rowOf(ev); if (!r || ev.button || ev.target.closest('button') || ev.target.tagName === 'INPUT') return; const id = r.id; let deferred = false; L.fromPanel = true;
    if (ev.ctrlKey || ev.metaKey) HD.sel.toggle(id);
    else if (ev.shiftKey && L.anchor && L.index.has(L.anchor)) { const a = L.index.get(L.anchor), b = L.index.get(id), out = []; for (let i = Math.min(a, b); i <= Math.max(a, b); i++) out.push(L.rows[i].id); HD.sel.set(out); }
    else if (!HD.sel.has(id)) HD.sel.set([id]); else deferred = true;
    if (!ev.shiftKey) L.anchor = id; L.scroll.focus({preventScroll: true});
    const y0 = ev.clientY, x0 = ev.clientX; let on = false, target = null, scrollT = 0;
    const mv = e2 => {
      if (!on) { if (Math.hypot(e2.clientX - x0, e2.clientY - y0) < 5 || !U().canEdit()) return; on = true; L.drag = true; document.body.classList.add('hd-dragging'); }
      const rc = L.scroll.getBoundingClientRect(), y = e2.clientY - rc.top + L.scroll.scrollTop; clearInterval(scrollT);
      if (e2.clientY < rc.top + 24) scrollT = setInterval(() => { L.scroll.scrollTop -= 14; }, 30); else if (e2.clientY > rc.bottom - 24) scrollT = setInterval(() => { L.scroll.scrollTop += 14; }, 30);
      let i = clamp(Math.floor(y / L.H), 0, L.rows.length - 1); const row = L.rows[i], fr = y / L.H - i, ids = sel(); target = null; for (const el of L.inner.querySelectorAll('.drop')) el.classList.remove('drop'); L.ind.hidden = true; if (!row) return;
      const isBox = !!HOLDS[U().typeOf(row.id)] && U().typeOf(row.id) !== 'INSTANCE'; let mode = fr < 0.5 ? 'above' : 'below'; if (isBox && fr > 0.28 && fr < 0.72) mode = 'in'; if (mode === 'below' && row.open) mode = 'in';
      let parent, before, depth = row.depth;
      if (mode === 'in') { parent = row.id; before = null; } else { parent = HD.store.parent(row.id); const sib = HD.store.children(parent), k = sib.indexOf(row.id); before = mode === 'above' ? (sib[k + 1] || null) : row.id; }
      for (const d of ids) if (d === parent || U().isInside(parent, d)) return; if (before && ids.indexOf(before) >= 0) { const sib = HD.store.children(parent); let k = sib.indexOf(before) + 1; while (k < sib.length && ids.indexOf(sib[k]) >= 0) k++; before = sib[k] || null; }
      target = {parent: parent, before: before};
      if (mode === 'in') { const el = L.inner.querySelector('.hd-lrow[data-id="' + row.id + '"]'); if (el) el.classList.add('drop'); }
      else { L.ind.hidden = false; L.ind.style.top = Math.max(1, (mode === 'above' ? i : i + 1) * L.H - 1) + 'px'; L.ind.style.left = (22 + depth * 14) + 'px'; }
    };
    const up = () => { window.removeEventListener('pointermove', mv); window.removeEventListener('pointerup', up); clearInterval(scrollT); document.body.classList.remove('hd-dragging'); L.drag = false; L.ind.hidden = true; for (const el of L.inner.querySelectorAll('.drop')) el.classList.remove('drop');
      if (on && target) { const ids = sel(); if (A().reparent(ids, target.parent, target.before)) { L.expanded.add(target.parent); L.dirty = true; L.fromPanel = true; HD.sel.set(ids.filter(x => HD.store.has(x))); } refresh(); }
      else if (!on && deferred && !ev.shiftKey) { L.fromPanel = true; HD.sel.set([id]); } };
    window.addEventListener('pointermove', mv); window.addEventListener('pointerup', up);
  }
  function layersKey(ev) {
    if (ev.target !== L.scroll) return; const ids = sel(), cur = ids.length ? L.index.get(ids[ids.length - 1]) : undefined;
    const go = i => { const r = L.rows[clamp(i, 0, L.rows.length - 1)]; if (!r) return; L.fromPanel = true; HD.sel.set([r.id]); L.anchor = r.id; const y = L.index.get(r.id) * L.H; if (y < L.scroll.scrollTop) L.scroll.scrollTop = y; else if (y + L.H > L.scroll.scrollTop + L.scroll.clientHeight) L.scroll.scrollTop = y + L.H - L.scroll.clientHeight; };
    if (ev.key === 'ArrowDown') { ev.preventDefault(); ev.stopPropagation(); go(cur === undefined ? 0 : cur + 1); }
    else if (ev.key === 'ArrowUp') { ev.preventDefault(); ev.stopPropagation(); go(cur === undefined ? 0 : cur - 1); }
    else if (ev.key === 'ArrowRight' && cur !== undefined) { ev.preventDefault(); ev.stopPropagation(); const r = L.rows[cur]; if (r.has && !r.open) { L.expanded.add(r.id); L.dirty = true; layersPaint(); } else if (r.has) go(cur + 1); }
    else if (ev.key === 'ArrowLeft' && cur !== undefined) { ev.preventDefault(); ev.stopPropagation(); const r = L.rows[cur]; if (r.open) { L.expanded.delete(r.id); L.dirty = true; layersPaint(); } else { const p = HD.store.parent(r.id); if (L.index.has(p)) go(L.index.get(p)); } }
    else if (ev.key === 'F2' && ids.length === 1) { ev.preventDefault(); renameLayer(ids[0]); }
  }
  function onSelChange() {
    const ids = sel(); if (!L.fromPanel && ids.length) reveal(ids); L.fromPanel = false; refresh();
  }

  /* ---------------------------------------------------------------- Design panel */
  const LAY_DEF = {mode: 'none', gap: 0, pad: [0, 0, 0, 0], alignMain: 'start', alignCross: 'start', wrap: false};
  function layOf(id) { return Object.assign({}, LAY_DEF, P(id, 'layout') || {}); }
  function isAuto(id) { const l = P(id, 'layout'); return !!(l && l.mode && l.mode !== 'none'); }
  function sigCount(ids, name) { const v = mixed(ids, name); return v === MIXED ? 'M' : Array.isArray(v) ? v.length + ':' + v.map(p => (p && p.type) || '').join(',') : '0'; }
  function designSig() {
    const ids = sel(); if (!ids.length) return 'none|' + HD.sel.page + '|' + U().canEdit() + '|' + !!hooks.exportSection;
    const s = v => v === MIXED ? 'M' : String(v);
    return [ids.length > 40 ? ids.length + ':' + ids[0] + ':' + ids[ids.length - 1] : ids.join(','), s(mixed(ids, id => U().typeOf(id))), sigCount(ids, 'fills'), sigCount(ids, 'strokes'), sigCount(ids, 'effects'),
      s(mixed(ids, id => isAuto(id) ? (layOf(id).wrap ? 'w' : layOf(id).mode) : 'none')), s(mixed(ids, id => isAuto(HD.store.parent(id)) ? 1 : 0)), s(mixed(ids, id => U().typeOf(HD.store.parent(id)))),
      ui.corners, ui.padEach, U().canEdit(), s(mixed(ids, id => Array.isArray(P(id, 'radius')))), !!hooks.exportSection].join('|');
  }
  function designPaint(el) {
    const sig = designSig(); if (sig === ui.sig && ui.designEl === el && el.firstChild) { for (const s of ui.syncs) { try { s(); } catch (e) { /* a stale control */ } } return; }
    ui.sig = sig; ui.designEl = el; ui.syncs = []; clear(el); const ids = sel();
    if (!ids.length) { designEmpty(el); return; }
    const types = new Set(ids.map(id => U().typeOf(id))), all = t => ids.every(id => t.indexOf(U().typeOf(id)) >= 0), edit = U().canEdit();
    const n0 = HD.store.get(ids[0]) || {};
    el.appendChild(h('div', {class: 'hd-selhead'}, h('span', {class: 'hd-ltype'}, icon(ids.length === 1 ? (TYPE_ICON[n0.type] || 'rect') : 'group', 14)), h('span', {class: 'hd-selname', text: ids.length === 1 ? (n0.name || n0.type) : ids.length + ' layers'}),
      h('span', {class: 'hd-seltype', text: ids.length === 1 ? typeLabel(n0.type) : types.size === 1 ? typeLabel(n0.type) + 's' : 'Mixed'})));
    /* align */
    const al = h('div', {class: 'hd-alignrow', role: 'toolbar', 'aria-label': 'Align'});
    for (const a of [['alL', 'Align left', 'left', 'alt+a'], ['alH', 'Align centre', 'hcenter', 'alt+h'], ['alR', 'Align right', 'right', 'alt+d'], ['alT', 'Align top', 'top', 'alt+w'], ['alV', 'Align middle', 'vcenter', 'alt+v'], ['alB', 'Align bottom', 'bottom', 'alt+s']]) { const b = ibtn(a[0], a[1] + '  (' + keysLabel(a[3]) + ')', () => A().align(a[2])); b.disabled = !edit; al.appendChild(b); }
    const more = ibtn('distH', 'Distribute and tidy up', ev => menu(ev.currentTarget, [{label: 'Distribute horizontally', icon: 'distH', keys: 'mod+alt+h', disabled: ids.length < 3, run: () => A().distribute('h')}, {label: 'Distribute vertically', icon: 'distV', keys: 'mod+alt+v', disabled: ids.length < 3, run: () => A().distribute('v')}, {label: 'Tidy up', icon: 'tidy', keys: 'mod+alt+t', disabled: ids.length < 2, run: () => A().tidy()}], {label: 'Distribute'})); more.disabled = !edit; al.appendChild(more);
    el.appendChild(al);
    secLayout(el, ids); if (all(['FRAME', 'COMPONENT'])) secAuto(el, ids); else if (edit) { const s = section(el, 'Auto layout', [{icon: 'plus', title: 'Wrap in an auto layout frame  (' + keysLabel('shift+a') + ')', run: addAutoLayout}], {cls: 'bare'}); void s; }
    secLayer(el, ids, all(['FRAME', 'COMPONENT', 'INSTANCE', 'SECTION']));
    if (all(['TEXT'])) secText(el, ids);
    if (!all(['GROUP']) || ids.length > 1 || ids.some(id => !!P(id, 'bool'))) { secPaints(el, ids, 'fills', 'Fill'); secPaints(el, ids, 'strokes', 'Stroke'); }   /* a boolean group is one shape: its own fill and stroke */
    secEffects(el, ids); secExport(el, ids);
    for (const f of designSecs) { try { f(el, ids); } catch (e) { if (window.console) console.error(e); } }
  }
  /* designSection(fn(el, ids)): a later phase adds its own section to the Design panel (built with HD.ui.section) */
  const designSecs = [];
  function designSection(fn) { if (typeof fn === 'function') { designSecs.push(fn); ui.sig = ''; refresh(); } }
  function typeLabel(t) { return ({RECT: 'Rectangle', ELLIPSE: 'Ellipse', LINE: 'Line', POLYGON: 'Polygon', STAR: 'Star', VECTOR: 'Vector', TEXT: 'Text', FRAME: 'Frame', GROUP: 'Group', SECTION: 'Section', COMPONENT: 'Component', COMPONENT_SET: 'Component set', INSTANCE: 'Instance'})[t] || 'Layer'; }
  function colorLine(o) {   /* swatch + hex + opacity for one paint; o: {get, set(p, g), title, solidOnly, remove, hide} */
    const sw = h('button', {class: 'hd-sw big', type: 'button', title: 'Change the colour', 'aria-label': (o.title || 'Colour') + ': change'}), hex = h('input', {class: 'hd-in hd-hex', type: 'text', 'aria-label': (o.title || 'Colour') + ' hex', spellcheck: 'false', maxlength: '24'}), op = h('input', {class: 'hd-in hd-opin', type: 'text', 'aria-label': (o.title || 'Colour') + ' opacity', inputmode: 'decimal'});
    const box = h('div', {class: 'hd-cbox'}, sw, hex, op), line = h('div', {class: 'hd-paint'}, o.grip || null, box);
    const eye = o.hide === false ? null : ibtn('eye', 'Show or hide', () => { const p = Object.assign({}, o.get()); p.visible = p.visible === false; o.set(p, null); }, 'sm'), rm = o.remove ? ibtn('minus', 'Remove', o.remove, 'sm') : null; add(line, [eye, rm]);
    const NAMES = {linear: 'Linear gradient', radial: 'Radial gradient', angular: 'Sweep gradient', image: 'Image'};
    function show() { const p = o.get(); if (!p) return; paintSwatch(sw, p); const solid = p.type === 'solid', edit = U().canEdit();
      if (document.activeElement !== hex) hex.value = solid ? String(p.color || '').replace('#', '') : (NAMES[p.type] || 'Paint'); hex.readOnly = !solid; hex.disabled = !edit; op.disabled = !edit; sw.disabled = !edit;
      if (document.activeElement !== op) op.value = fmt((p.opacity === undefined ? 1 : p.opacity) * 100, 0) + '%'; line.classList.toggle('off', p.visible === false);
      if (eye) { clear(eye).appendChild(icon(p.visible === false ? 'eyeoff' : 'eye')); eye.disabled = !edit; } if (rm) rm.disabled = !edit; }
    sw.addEventListener('click', () => paintPicker(box, {get: o.get, set: o.set, solidOnly: o.solidOnly, title: o.title, level: o.level || 0}));
    hex.addEventListener('focus', () => { if (!hex.readOnly) setTimeout(() => hex.select(), 0); else sw.click(); });
    hex.addEventListener('change', () => { const p = o.get(); if (!p || p.type !== 'solid') return; const c = parseColor(hex.value); if (c) { const q = Object.assign({}, p, {color: c.hex}); if (c.a !== null) q.opacity = c.a; o.set(q, null); pushRecent(c.hex); } show(); });
    hex.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); hex.blur(); } }); op.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); op.blur(); } });
    op.addEventListener('focus', () => setTimeout(() => op.select(), 0));
    op.addEventListener('change', () => { const p = o.get(), v = calc(op.value, (p.opacity === undefined ? 1 : p.opacity) * 100, '%'); if (p && v !== null) o.set(Object.assign({}, p, {opacity: clamp(v / 100, 0, 1)}), null); show(); });
    ui.syncs.push(show); show(); return line;
  }
  function designEmpty(el) {
    const pg = HD.sel.page, s = section(el, 'Page');
    s.body.appendChild(colorLine({title: 'Page background', solidOnly: true, hide: false, get: () => ({type: 'solid', color: P(pg, 'bg') || '#F5F5F5', opacity: 1}), set: (p, g) => write('Page background', () => HD.store.set(pg, {bg: p.color}), g)}));
    const tips = section(el, 'Getting started');
    for (const t of [['frame', 'Frame', 'F', 'A screen, a card, a poster'], ['rect', 'Rectangle', 'R', 'Drag on the canvas to draw'], ['text', 'Text', 'T', 'Click to type, in any language'], ['pen', 'Pen', 'P', 'Click for corners, drag for curves']])
      tips.body.appendChild(h('button', {class: 'hd-tip', type: 'button', disabled: !U().canEdit(), on: {click: () => T().set(t[0])}}, h('span', {class: 'hd-tip-ic'}, icon(t[0], 16)), h('span', {class: 'hd-tip-t'}, h('b', {text: t[1]}), h('span', {text: t[3]})), h('kbd', {text: t[2]})));
    tips.body.appendChild(h('button', {class: 'hd-linkbtn', type: 'button', text: 'All keyboard shortcuts', on: {click: shortcutSheet}}));
  }
  const ROUNDS = {RECT: 1, FRAME: 1, COMPONENT: 1, INSTANCE: 1, SECTION: 1, POLYGON: 1, STAR: 1}, CORNERS = {RECT: 1, FRAME: 1, COMPONENT: 1, INSTANCE: 1, SECTION: 1};
  function secLayout(el, ids) {
    const s = section(el, 'Layout'), inFlow = id => isAuto(HD.store.parent(id)) && P(id, 'layoutPos') !== 'absolute', allFlow = ids.every(inFlow), anyAutoPar = ids.some(id => isAuto(HD.store.parent(id)));
    const geo = (name, title, label, o) => numField(Object.assign({label: label, title: title, get: () => mixed(ids, id => U().num(id, name, name === 'w' || name === 'h' ? 100 : 0)), set: (v, g) => write(title, () => { for (const id of ids) HD.store.set(id, {[name]: v}); }, g)}, o || {}));
    const sizeSet = (axis) => (v, g) => write(axis === 'w' ? 'Width' : 'Height', () => { for (const id of ids) { const w0 = U().num(id, 'w', 100), h0 = U().num(id, 'h', 100), r = ui.ratio && w0 && h0 ? w0 / h0 : 0;
      if (axis === 'w') A().resizeTo(id, v, r ? v / r : undefined); else A().resizeTo(id, r ? v * r : undefined, v); const side = axis === 'w' ? 'sizeH' : 'sizeV'; if (P(id, side) && P(id, side) !== 'fixed') HD.store.set(id, {[side]: 'fixed'}); } }, g);
    s.body.appendChild(row(geo('x', 'X position', 'X', {off: () => allFlow}), geo('y', 'Y position', 'Y', {off: () => allFlow})));
    const line = ids.every(id => U().typeOf(id) === 'LINE');
    s.body.appendChild(row(numField({label: 'W', title: 'Width', min: 0.01, get: () => mixed(ids, id => U().num(id, 'w', 100)), set: sizeSet('w')}),
      line ? h('span', {class: 'hd-field ghost'}) : numField({label: 'H', title: 'Height', min: 0.01, get: () => mixed(ids, id => U().num(id, 'h', 100)), set: sizeSet('h')}),
      toggle('link', 'Keep the proportions', () => ui.ratio, v => { ui.ratio = v; }, 'sm')));
    const hasAuto = ids.some(isAuto), isText = ids.every(id => U().typeOf(id) === 'TEXT');
    if (anyAutoPar || hasAuto) { const opts = side => { const o = [['fixed', 'Fixed']]; if (hasAuto || isText) o.push(['hug', 'Hug']); if (anyAutoPar) o.push(['fill', 'Fill']); void side; return o; };
      s.body.appendChild(row(h('label', {class: 'hd-sfield'}, h('span', {class: 'hd-flab', text: 'W'}), select(opts('h'), () => mixed(ids, 'sizeH') || 'fixed', v => setAll('Resizing', ids, 'sizeH', v), 'Horizontal resizing')),
        h('label', {class: 'hd-sfield'}, h('span', {class: 'hd-flab', text: 'H'}), select(opts('v'), () => mixed(ids, 'sizeV') || 'fixed', v => setAll('Resizing', ids, 'sizeV', v), 'Vertical resizing')), h('span', {class: 'hd-ib sm ghost'}))); }
    s.body.appendChild(row(geo('rot', 'Rotation', null, {icon: 'rotate', unit: '°', min: -360, max: 360}),
      !ids.some(id => ROUNDS[U().typeOf(id)]) ? h('span', {class: 'hd-field ghost'}) : numField({icon: 'radius', title: 'Corner radius', min: 0, off: () => ui.corners, get: () => mixed(ids, id => { const r = P(id, 'radius'); return Array.isArray(r) ? (r.every(x => x === r[0]) ? r[0] : MIXED) : (r || 0); }), set: (v, g) => setAll('Corner radius', ids, 'radius', v, g)}),
      ids.some(id => CORNERS[U().typeOf(id)]) ? toggle('corners', 'Set each corner on its own', () => ui.corners, v => { ui.corners = v; refresh(); }, 'sm') : h('span', {class: 'hd-ib sm ghost'})));
    if (ui.corners && ids.some(id => CORNERS[U().typeOf(id)])) { const names = ['Top left', 'Top right', 'Bottom right', 'Bottom left'], r = h('div', {class: 'hd-row four'});
      names.forEach((nm, i) => r.appendChild(numField({label: ['⌜', '⌝', '⌟', '⌞'][i], title: nm + ' radius', min: 0, get: () => mixed(ids, id => { const v = P(id, 'radius'); return Array.isArray(v) ? (v[i] || 0) : (v || 0); }),
        set: (v, g) => write('Corner radius', () => { for (const id of ids) { const c = P(id, 'radius'), arr = Array.isArray(c) ? c.slice(0, 4) : [c || 0, c || 0, c || 0, c || 0]; while (arr.length < 4) arr.push(0); arr[i] = v; HD.store.set(id, {radius: arr}); } }, g)}))); s.body.appendChild(r); }
    const acts = h('div', {class: 'hd-row tight'}, ibtn('flipH', 'Flip horizontal  (' + keysLabel('shift+h') + ')', () => A().flip('h'), 'sm'), ibtn('flipV', 'Flip vertical  (' + keysLabel('shift+v') + ')', () => A().flip('v'), 'sm'));
    if (anyAutoPar) acts.appendChild(h('label', {class: 'hd-check'}, checkbox(() => mixed(ids, id => P(id, 'layoutPos') === 'absolute'), v => setAll('Absolute position', ids, 'layoutPos', v ? 'absolute' : 'auto'), 'Ignore auto layout'), h('span', {text: 'Ignore auto layout'})));
    s.body.appendChild(acts);
    /* constraints: only for layers that sit freely inside a frame */
    const free = ids.every(id => { const p = HD.store.parent(id), t = U().typeOf(p); return (t === 'FRAME' || t === 'COMPONENT' || t === 'INSTANCE') && !isAuto(p); });
    if (free) { const c = section(el, 'Constraints'), cons = id => Object.assign({h: 'left', v: 'top'}, P(id, 'cons') || {});
      const setC = (k, v) => write('Constraints', () => { for (const id of ids) HD.store.set(id, {cons: Object.assign(cons(id), {[k]: v})}); });
      c.body.appendChild(row(h('label', {class: 'hd-sfield'}, h('span', {class: 'hd-flab'}, icon('hdir', 14)), select([['left', 'Left'], ['right', 'Right'], ['leftright', 'Left and right'], ['center', 'Centre'], ['scale', 'Scale']], () => mixed(ids, id => cons(id).h), v => setC('h', v), 'Horizontal constraint')),
        h('label', {class: 'hd-sfield'}, h('span', {class: 'hd-flab'}, icon('vdir', 14)), select([['top', 'Top'], ['bottom', 'Bottom'], ['topbottom', 'Top and bottom'], ['center', 'Centre'], ['scale', 'Scale']], () => mixed(ids, id => cons(id).v), v => setC('v', v), 'Vertical constraint')))); }
  }
  function checkbox(get, set, label) { const c = h('input', {type: 'checkbox', class: 'hd-cb', 'aria-label': label}); c.addEventListener('change', () => set(c.checked)); const show = () => { const v = get(); c.indeterminate = v === MIXED; c.checked = v === true; c.disabled = !U().canEdit(); }; ui.syncs.push(show); show(); return c; }
  function addAutoLayout() {
    if (!U().canEdit()) return; let ids = sel(); if (!ids.length) return;
    const direct = ids.length === 1 && (U().typeOf(ids[0]) === 'FRAME' || U().typeOf(ids[0]) === 'COMPONENT') && !isAuto(ids[0]);
    HD.store.tx('Add auto layout', () => {
      let fid = direct ? ids[0] : A().wrap('FRAME'); if (!fid) return; const kids = HD.store.children(fid).filter(k => P(k, 'visible') !== false); let mode = 'v', gap = 10, pad = [10, 10, 10, 10];
      if (kids.length) { const bs = kids.map(k => U().aabb(k)), u = U().union(kids), fb = U().aabb(fid); let spreadX = 0, spreadY = 0; for (const b of bs) { spreadX = Math.max(spreadX, b.x + b.w / 2); spreadY = Math.max(spreadY, b.y + b.h / 2); }
        const minX = Math.min.apply(null, bs.map(b => b.x + b.w / 2)), minY = Math.min.apply(null, bs.map(b => b.y + b.h / 2)); mode = (spreadX - minX) > (spreadY - minY) ? 'h' : 'v';
        const sorted = bs.slice().sort((a, b) => mode === 'h' ? a.x - b.x : a.y - b.y), gaps = []; for (let i = 1; i < sorted.length; i++) gaps.push(mode === 'h' ? sorted[i].x - (sorted[i - 1].x + sorted[i - 1].w) : sorted[i].y - (sorted[i - 1].y + sorted[i - 1].h));
        if (gaps.length) gap = Math.max(0, Math.round(gaps.reduce((a, b) => a + b, 0) / gaps.length));
        pad = direct ? [Math.max(0, Math.round(u.y - fb.y)), Math.max(0, Math.round(fb.x + fb.w - u.x - u.w)), Math.max(0, Math.round(fb.y + fb.h - u.y - u.h)), Math.max(0, Math.round(u.x - fb.x))] : [0, 0, 0, 0]; }
      HD.store.set(fid, {layout: {mode: mode, gap: gap, pad: pad, alignMain: 'start', alignCross: 'start', wrap: false}, sizeH: 'hug', sizeV: 'hug'});
    });
  }
  function secAuto(el, ids) {
    const on = ids.every(isAuto), edit = U().canEdit();
    const setL = (patch, g, label) => write(label || 'Auto layout', () => { for (const id of ids) HD.store.set(id, {layout: Object.assign(layOf(id), typeof patch === 'function' ? patch(layOf(id)) : patch)}); }, g);
    if (!on) { if (edit) section(el, 'Auto layout', [{icon: 'plus', title: 'Add auto layout  (' + keysLabel('shift+a') + ')', run: addAutoLayout}], {cls: 'bare'}); return; }
    const s = section(el, 'Auto layout', [edit ? {icon: 'minus', title: 'Remove auto layout', run: () => write('Remove auto layout', () => { for (const id of ids) HD.store.set(id, {layout: Object.assign(layOf(id), {mode: 'none'}), sizeH: 'fixed', sizeV: 'fixed'}); })} : null]);
    const dir = () => mixed(ids, id => { const l = layOf(id); return l.wrap ? 'wrap' : l.mode; });
    s.body.appendChild(row(seg([{v: 'v', icon: 'vdir', title: 'Stack downwards'}, {v: 'h', icon: 'hdir', title: 'Line up sideways'}, {v: 'wrap', icon: 'wrap', title: 'Wrap onto new lines'}], dir, v => setL(v === 'wrap' ? {mode: 'h', wrap: true} : {mode: v, wrap: false}), 'Direction'),
      numField({icon: 'gap', title: 'Gap between items', min: -999, words: {auto: 'auto'}, get: () => mixed(ids, id => layOf(id).alignMain === 'between' ? 'auto' : layOf(id).gap || 0), set: (v, g) => setL(v === 'auto' ? {alignMain: 'between'} : l => ({gap: v, alignMain: l.alignMain === 'between' ? 'start' : l.alignMain}), g, 'Gap')})));
    const padGet = idxs => () => mixed(ids, id => { const p = layOf(id).pad || [0, 0, 0, 0]; return idxs.every(i => (p[i] || 0) === (p[idxs[0]] || 0)) ? (p[idxs[0]] || 0) : MIXED; });
    const padSet = idxs => (v, g) => setL(l => { const p = (l.pad || [0, 0, 0, 0]).slice(0, 4); while (p.length < 4) p.push(0); for (const i of idxs) p[i] = v; return {pad: p}; }, g, 'Padding');
    if (!ui.padEach) s.body.appendChild(row(numField({icon: 'padh', title: 'Padding left and right', min: 0, get: padGet([3, 1]), set: padSet([3, 1])}), numField({icon: 'padv', title: 'Padding top and bottom', min: 0, get: padGet([0, 2]), set: padSet([0, 2])}), toggle('corners', 'Set each side on its own', () => ui.padEach, v => { ui.padEach = v; refresh(); }, 'sm')));
    else { const r = h('div', {class: 'hd-row four'}); [['T', 'Padding top', 0], ['R', 'Padding right', 1], ['B', 'Padding bottom', 2], ['L', 'Padding left', 3]].forEach(a => r.appendChild(numField({label: a[0], title: a[1], min: 0, get: padGet([a[2]]), set: padSet([a[2]])})));
      s.body.appendChild(row(h('span', {class: 'hd-dimtext', text: 'Padding'}), h('span', {class: 'hd-grow1'}), toggle('corners', 'Set each side on its own', () => ui.padEach, v => { ui.padEach = v; refresh(); }, 'sm'))); s.body.appendChild(r); }
    /* 3 x 3 alignment */
    const grid = h('div', {class: 'hd-agrid', role: 'radiogroup', 'aria-label': 'Align the items'}), POS = ['start', 'center', 'end'], NM = {start: ['left', 'top'], center: ['centre', 'middle'], end: ['right', 'bottom']};
    for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) { const b = h('button', {class: 'hd-acell', type: 'button', role: 'radio', 'data-r': r, 'data-c': c, title: 'Align ' + NM[POS[r]][1] + ' ' + NM[POS[c]][0], 'aria-label': 'Align ' + NM[POS[r]][1] + ' ' + NM[POS[c]][0]}, h('i'));
      b.addEventListener('click', () => setL(l => l.mode === 'h' ? {alignMain: l.alignMain === 'between' ? 'between' : POS[c], alignCross: POS[r]} : {alignMain: l.alignMain === 'between' ? 'between' : POS[r], alignCross: POS[c]}, null, 'Align items')); grid.appendChild(b); }
    const showGrid = () => { const l = ids.length ? layOf(ids[0]) : LAY_DEF, mx = mixed(ids, id => { const k = layOf(id); return k.mode + k.alignMain + k.alignCross; }) === MIXED, main = l.alignMain === 'between' ? -1 : POS.indexOf(l.alignMain), cross = Math.max(0, POS.indexOf(l.alignCross === 'stretch' ? 'start' : l.alignCross));
      for (const b of grid.children) { const r = +b.dataset.r, c = +b.dataset.c, on = !mx && (l.mode === 'h' ? (r === cross && (main < 0 || c === main)) : (c === cross && (main < 0 || r === main))); b.classList.toggle('on', on); b.setAttribute('aria-checked', String(on)); b.disabled = !edit; } grid.dataset.mode = l.mode; };
    ui.syncs.push(showGrid); showGrid();
    s.body.appendChild(row(grid, h('div', {class: 'hd-acol'}, h('label', {class: 'hd-check'}, checkbox(() => mixed(ids, id => layOf(id).alignMain === 'between'), v => setL({alignMain: v ? 'between' : 'start'}), 'Space between'), h('span', {text: 'Space between'})),
      h('label', {class: 'hd-check'}, checkbox(() => mixed(ids, id => layOf(id).alignCross === 'stretch'), v => setL({alignCross: v ? 'stretch' : 'start'}), 'Stretch items'), h('span', {text: 'Stretch items'})))));
  }
  const BLENDS = [['normal', 'Normal'], ['multiply', 'Multiply'], ['screen', 'Screen'], ['overlay', 'Overlay'], ['darken', 'Darken'], ['lighten', 'Lighten'], ['color-dodge', 'Colour dodge'], ['color-burn', 'Colour burn'], ['hard-light', 'Hard light'], ['soft-light', 'Soft light'], ['difference', 'Difference'], ['exclusion', 'Exclusion'], ['hue', 'Hue'], ['saturation', 'Saturation'], ['color', 'Colour'], ['luminosity', 'Luminosity']];
  function secLayer(el, ids, frames) {
    const s = section(el, 'Layer');
    s.body.appendChild(row(numField({icon: 'opacity', title: 'Opacity', unit: '%', min: 0, max: 100, get: () => { const v = mixed(ids, id => { const o = P(id, 'opacity'); return typeof o === 'number' ? o : 1; }); return v === MIXED ? MIXED : Math.round(v * 100); }, set: (v, g) => setAll('Opacity', ids, 'opacity', Math.round(v) / 100, g)}),
      h('label', {class: 'hd-sfield grow'}, select(BLENDS, () => mixed(ids, 'blend') || 'normal', v => setAll('Blend mode', ids, 'blend', v), 'Blend mode'))));
    if (frames) s.body.appendChild(row(h('label', {class: 'hd-check'}, checkbox(() => mixed(ids, id => P(id, 'clip') === true), v => setAll('Clip content', ids, 'clip', v), 'Clip content'), h('span', {text: 'Clip content'}))));
  }
  function secText(el, ids) {
    const s = section(el, 'Text'), fam = () => mixed(ids, 'font') || 'Inter';
    const fbtn = h('button', {class: 'hd-fontbtn', type: 'button', title: 'Font', 'aria-haspopup': 'listbox'}, h('span', {class: 'hd-fontname'}), icon('down', 10));
    fbtn.addEventListener('click', () => fontPicker(fbtn, fam() === MIXED ? '' : fam(), f => { loadFont(f);
      const ws = fontWeights(f); write('Font', () => { for (const id of ids) { const w = U().num(id, 'fontWeight', 400), p = {font: f}; if (ws.indexOf(w) < 0) p.fontWeight = ws.reduce((a, b) => Math.abs(b - w) < Math.abs(a - w) ? b : a, ws[0]); HD.store.set(id, p); } }); refresh(); }));
    ui.syncs.push(() => { const f = fam(); fbtn.firstChild.textContent = f === MIXED ? 'Mixed' : f; fbtn.disabled = !U().canEdit(); if (f !== MIXED) loadFont(f); }); fbtn.firstChild.textContent = fam() === MIXED ? 'Mixed' : fam();
    s.body.appendChild(row(fbtn));
    const wsel = h('select', {class: 'hd-sel', 'aria-label': 'Font weight', title: 'Font weight'}); let wsFor = null;
    const showW = () => { const f = fam(), list = f === MIXED ? [300, 400, 500, 600, 700] : fontWeights(f), key = list.join(); if (key !== wsFor) { wsFor = key; clear(wsel); wsel.appendChild(h('option', {value: '__mixed', text: 'Mixed', hidden: true, disabled: true})); for (const w of list) wsel.appendChild(h('option', {value: String(w), text: WEIGHT_NAME[w] || String(w)})); }
      if (document.activeElement !== wsel) { const v = mixed(ids, id => U().num(id, 'fontWeight', 400)); wsel.value = v === MIXED ? '__mixed' : String(v); if (wsel.selectedIndex < 0) wsel.value = '__mixed'; } wsel.disabled = !U().canEdit(); };
    wsel.addEventListener('change', () => { const v = parseInt(wsel.value, 10); if (v) setAll('Font weight', ids, 'fontWeight', v); }); ui.syncs.push(showW); showW();
    s.body.appendChild(row(h('label', {class: 'hd-sfield grow'}, wsel), numField({label: 'Size', title: 'Font size', min: 1, max: 2000, get: () => mixed(ids, id => U().num(id, 'fontSize', 16)), set: (v, g) => setAll('Font size', ids, 'fontSize', v, g)})));
    s.body.appendChild(row(numField({icon: 'lh', title: 'Line height (a number, or auto)', min: 0, words: {auto: 'auto', '': 'auto'}, get: () => mixed(ids, id => { const v = P(id, 'lineHeight'); return typeof v === 'number' ? v : 'auto'; }), set: (v, g) => setAll('Line height', ids, 'lineHeight', v, g)}),
      numField({icon: 'ls', title: 'Letter spacing', step: 0.1, min: -100, max: 500, get: () => mixed(ids, id => U().num(id, 'letterSpacing', 0)), set: (v, g) => setAll('Letter spacing', ids, 'letterSpacing', v, g)})));
    const sg = (name, opts, label, def) => seg(opts, () => { const v = mixed(ids, name); return v === undefined ? def : v; }, v => setAll(label, ids, name, v), label);
    s.body.appendChild(row(sg('align', [{v: 'left', icon: 'tleft', title: 'Align left'}, {v: 'center', icon: 'tcenter', title: 'Align centre'}, {v: 'right', icon: 'tright', title: 'Align right'}, {v: 'justify', icon: 'tjust', title: 'Justify'}], 'Text align', 'left'),
      sg('alignV', [{v: 'top', icon: 'vtop', title: 'Align top'}, {v: 'middle', icon: 'vmid', title: 'Align middle'}, {v: 'bottom', icon: 'vbot', title: 'Align bottom'}], 'Vertical align', 'top')));
    s.body.appendChild(row(sg('autoResize', [{v: 'wh', icon: 'autow', title: 'Grow sideways with the text'}, {v: 'h', icon: 'autoh', title: 'Fixed width, grows downwards'}, {v: 'none', icon: 'fixed', title: 'Fixed size'}], 'Resizing', 'wh'),
      sg('decoration', [{v: 'none', text: '–', title: 'No decoration'}, {v: 'underline', text: 'U', title: 'Underline'}, {v: 'strike', text: 'S', title: 'Strikethrough'}], 'Decoration', 'none')));
    s.body.appendChild(row(sg('textCase', [{v: 'none', text: '–', title: 'As typed'}, {v: 'upper', text: 'AG', title: 'Upper case'}, {v: 'lower', text: 'ag', title: 'Lower case'}, {v: 'title', text: 'Ag', title: 'Title case'}], 'Letter case', 'none'),
      h('label', {class: 'hd-check'}, checkbox(() => mixed(ids, id => P(id, 'italic') === true), v => setAll('Italic', ids, 'italic', v), 'Italic'), h('span', {text: 'Italic'}))));
  }
  function secPaints(el, ids, name, title) {
    const val = mixed(ids, name), edit = U().canEdit(), list = () => { const v = P(ids[0], name); return Array.isArray(v) ? v : []; };
    const setList = (arr, g) => write(title, () => { for (const id of ids) HD.store.set(id, {[name]: arr}); }, g);
    const addPaint = () => { const base = val === MIXED ? [] : list().slice(); base.push({type: 'solid', color: name === 'fills' ? '#D9D9D9' : '#1A1A1F', opacity: 1, visible: true}); setList(base); };
    const s = section(el, title, [edit ? {icon: 'plus', title: 'Add a ' + title.toLowerCase(), run: addPaint} : null], {cls: (val !== MIXED && !list().length) ? 'bare' : ''});
    if (val === MIXED) { s.body.appendChild(h('p', {class: 'hd-note', text: 'These layers have different ' + title.toLowerCase() + 's. Press + to give them all the same one.'})); return; }
    const n = list().length;
    for (let i = n - 1; i >= 0; i--) { const grip = n > 1 && edit ? h('span', {class: 'hd-grip', title: 'Drag to reorder', 'aria-hidden': 'true'}, icon('grip', 12)) : null;
      const line = colorLine({title: title, grip: grip, get: () => list()[i], set: (p, g) => { const a = list().slice(); if (i < a.length) { a[i] = p; setList(a, g); } }, remove: () => { const a = list().slice(); a.splice(i, 1); setList(a); }});
      line.dataset.i = String(i); if (grip) paintDrag(grip, line, s.body, (from, to) => { const a = list().slice(), it = a.splice(from, 1)[0]; a.splice(to, 0, it); setList(a); });
      s.body.appendChild(line); }
    if (name === 'strokes' && n) {
      s.body.appendChild(row(numField({label: 'Weight', wide: true, title: 'Stroke weight', min: 0, max: 1000, get: () => mixed(ids, id => U().num(id, 'strokeWeight', 1)), set: (v, g) => setAll('Stroke weight', ids, 'strokeWeight', v, g)}),
        h('label', {class: 'hd-sfield grow'}, select([['center', 'Centre'], ['inside', 'Inside'], ['outside', 'Outside']], () => mixed(ids, 'strokeAlign') || 'center', v => setAll('Stroke position', ids, 'strokeAlign', v), 'Stroke position'))));
      s.body.appendChild(row(h('label', {class: 'hd-sfield grow'}, select([['butt', 'Flat ends'], ['round', 'Round ends'], ['square', 'Square ends']], () => mixed(ids, 'strokeCap') || 'butt', v => setAll('Line ends', ids, 'strokeCap', v), 'Line ends')),
        h('label', {class: 'hd-sfield grow'}, select([['miter', 'Sharp joins'], ['round', 'Round joins'], ['bevel', 'Cut joins']], () => mixed(ids, 'strokeJoin') || 'miter', v => setAll('Line joins', ids, 'strokeJoin', v), 'Line joins'))));
      const dash = h('input', {class: 'hd-in', type: 'text', placeholder: 'Solid', 'aria-label': 'Dashes (dash, gap)', spellcheck: 'false'}), showD = () => { if (document.activeElement === dash) return; const v = mixed(ids, 'dash'); dash.value = v === MIXED ? 'Mixed' : Array.isArray(v) && v.length ? v.join(', ') : ''; dash.disabled = !U().canEdit(); };
      dash.addEventListener('change', () => { const arr = dash.value.split(/[\s,]+/).map(parseFloat).filter(v => isFinite(v) && v >= 0).slice(0, 8); setAll('Dashes', ids, 'dash', arr); showD(); }); dash.addEventListener('keydown', ev => { if (ev.key === 'Enter') dash.blur(); }); ui.syncs.push(showD); showD();
      s.body.appendChild(row(h('label', {class: 'hd-field wide', title: 'Dashes: dash length, gap (for example 6, 4)'}, h('span', {class: 'hd-flab', text: 'Dashes'}), dash)));
    }
  }
  function paintDrag(grip, line, body, done) {
    grip.addEventListener('pointerdown', ev => { if (ev.button) return; ev.preventDefault(); const lines = Array.from(body.querySelectorAll('.hd-paint')); let target = null; line.classList.add('drag');
      const mv = e2 => { target = null; for (const l of lines) l.classList.remove('dropb'); for (const l of lines) { const r = l.getBoundingClientRect(); if (e2.clientY >= r.top && e2.clientY <= r.bottom && l !== line) { target = l; l.classList.add('dropb'); } } };
      const up = () => { window.removeEventListener('pointermove', mv); window.removeEventListener('pointerup', up); line.classList.remove('drag'); for (const l of lines) l.classList.remove('dropb'); if (target) done(+line.dataset.i, +target.dataset.i); };
      window.addEventListener('pointermove', mv); window.addEventListener('pointerup', up); });
  }
  const FX = [['drop', 'Drop shadow'], ['inner', 'Inner shadow'], ['blur', 'Layer blur'], ['bgblur', 'Background blur']];
  function secEffects(el, ids) {
    const val = mixed(ids, 'effects'), edit = U().canEdit(), list = () => { const v = P(ids[0], 'effects'); return Array.isArray(v) ? v : []; };
    const setList = (arr, g) => write('Effects', () => { for (const id of ids) HD.store.set(id, {effects: arr}); }, g);
    const fresh = t => t === 'drop' || t === 'inner' ? {type: t, x: 0, y: 4, blur: 12, spread: 0, color: '#000000', opacity: 0.25, visible: true} : {type: t, blur: 8, visible: true};
    const s = section(el, 'Effects', [edit ? {icon: 'plus', title: 'Add an effect', run: () => { const a = val === MIXED ? [] : list().slice(); a.push(fresh('drop')); setList(a); }} : null], {cls: (val !== MIXED && !list().length) ? 'bare' : ''});
    if (val === MIXED) { s.body.appendChild(h('p', {class: 'hd-note', text: 'These layers have different effects. Press + to give them all the same one.'})); return; }
    list().forEach((fx, i) => {
      const upd = (patch, g) => { const a = list().slice(); if (i < a.length) { a[i] = Object.assign({}, a[i], patch); setList(a, g); } };
      const tsel = select(FX, () => (list()[i] || {}).type, v => { const a = list().slice(), old = a[i] || {}; a[i] = Object.assign(fresh(v), {visible: old.visible !== false}, (v === 'drop' || v === 'inner') && (old.type === 'drop' || old.type === 'inner') ? {x: old.x, y: old.y, blur: old.blur, spread: old.spread, color: old.color, opacity: old.opacity} : {blur: old.blur || 8}); setList(a); }, 'Effect type');
      const line = h('div', {class: 'hd-paint fx'});
      const setBtn = ibtn('sliders', 'Effect settings', () => { const cur = () => list()[i] || fresh('drop'), body = h('div', {class: 'hd-fxpop'}), shadow = cur().type === 'drop' || cur().type === 'inner';
        const nf = (key, label, o) => numField(Object.assign({label: label, title: label, get: () => cur()[key] || 0, set: (v, g) => upd({[key]: v}, g)}, o || {}));
        body.appendChild(h('div', {class: 'hd-phead'}, h('span', {class: 'hd-ptitle', text: (FX.find(f => f[0] === cur().type) || FX[0])[1]}), ibtn('close', 'Close', () => hp.close())));
        if (shadow) { body.appendChild(row(nf('x', 'X'), nf('y', 'Y'))); body.appendChild(row(nf('blur', 'Blur', {min: 0}), nf('spread', 'Spread'))); body.appendChild(colorLine({title: 'Shadow colour', solidOnly: true, hide: false, level: 1, get: () => ({type: 'solid', color: cur().color || '#000000', opacity: cur().opacity === undefined ? 1 : cur().opacity}), set: (p, g) => upd({color: p.color, opacity: p.opacity}, g)})); }
        else body.appendChild(row(nf('blur', 'Blur', {min: 0, wide: true})));
        const hp = pop(line, body, {cls: 'hd-pop-fx', label: 'Effect settings', side: 'left'}); }, 'sm');
      const eye = ibtn('eye', 'Show or hide', () => upd({visible: (list()[i] || {}).visible === false}), 'sm'), rm = ibtn('minus', 'Remove', () => { const a = list().slice(); a.splice(i, 1); setList(a); }, 'sm');
      const showFx = () => { const f = list()[i]; if (!f) return; line.classList.toggle('off', f.visible === false); clear(eye).appendChild(icon(f.visible === false ? 'eyeoff' : 'eye')); for (const b of [setBtn, eye, rm]) b.disabled = !U().canEdit(); }; ui.syncs.push(showFx); showFx();
      add(line, [h('label', {class: 'hd-sfield grow'}, tsel), setBtn, eye, rm]); s.body.appendChild(line); void fx;
    });
  }
  function secExport(el, ids) {
    const s = section(el, 'Export', [{icon: 'plus', title: 'Export these layers', run: () => fire('export', ids)}], {cls: 'bare'});
    if (hooks.exportSection) { s.el.classList.remove('bare'); try { hooks.exportSection(s.body, ids); } catch (e) { /* the export phase owns this */ } }
  }

  /* ---------------------------------------------------------------- context menu, palette, shortcut sheet */
  function contextMenu(x, y, e) {
    const ids = sel(), edit = U().canEdit(), has = ids.length > 0, at = e ? [e.x, e.y] : undefined, clip = A().clip();
    const holds = ids.some(id => HOLDS[U().typeOf(id)] && HD.store.children(id).length), locked = has && ids.every(id => P(id, 'locked') === true), hid = has && ids.every(id => P(id, 'visible') === false);
    const extra = (menus.context || []).map(m => typeof m === 'function' ? m(ids, e) : m).filter(Boolean);
    menu({x: x, y: y}, [
      has && {label: 'Copy', keys: 'mod+c', run: () => A().copy()}, has && edit && {label: 'Cut', keys: 'mod+x', run: () => A().cut()},
      edit && {label: 'Paste here', keys: 'mod+v', disabled: !clip, run: () => A().paste(at)}, has && edit && {label: 'Duplicate', keys: 'mod+d', run: () => A().duplicate()}, has && edit && {label: 'Delete', keys: 'delete', danger: true, run: () => A().remove()}, '-',
      has && edit && {label: 'Bring to front', keys: ']', run: () => A().order('front')}, has && edit && {label: 'Bring forward', keys: 'mod+]', run: () => A().order('forward')}, has && edit && {label: 'Send backward', keys: 'mod+[', run: () => A().order('backward')}, has && edit && {label: 'Send to back', keys: '[', run: () => A().order('back')}, '-',
      has && edit && {label: 'Group', keys: 'mod+g', run: () => A().group()}, has && edit && {label: 'Frame selection', keys: 'mod+alt+g', run: () => A().frameSelection()}, holds && edit && {label: 'Ungroup', keys: 'mod+shift+g', run: () => A().ungroup()}, has && edit && {label: 'Add auto layout', keys: 'shift+a', run: addAutoLayout}, '-',
      has && edit && {label: 'Flip horizontal', keys: 'shift+h', run: () => A().flip('h')}, has && edit && {label: 'Flip vertical', keys: 'shift+v', run: () => A().flip('v')}, '-',
      has && edit && ids.length === 1 && {label: 'Rename', keys: 'mod+r', run: () => renameLayer(ids[0])}, has && edit && {label: locked ? 'Unlock' : 'Lock', keys: 'mod+shift+l', run: () => A().toggle('locked')}, has && edit && {label: hid ? 'Show' : 'Hide', keys: 'mod+shift+h', run: () => A().toggle('visible')}, '-',
      !has && {label: 'Select all', keys: 'mod+a', run: () => A().selectAll()}, !has && {label: 'Zoom to fit', keys: 'shift+1', run: () => T().view.fit()}, has && {label: 'Zoom to selection', keys: 'shift+2', run: () => A().zoomSelection()},
      has && {label: 'Export…', keys: 'mod+shift+e', run: () => fire('export', ids)}, !has && {label: ui.hidden ? 'Show the panels' : 'Hide the panels', keys: 'mod+\\', run: toggleUI}
    ].concat(extra.length ? ['-'] : []).concat(extra), {label: 'Layer menu'});
  }
  const modal = {el: null};
  function closeModal() { if (!modal.el) return; const m = modal.el; modal.el = null; if (m.parentNode) m.parentNode.removeChild(m); if (modal.back && document.contains(modal.back)) { try { modal.back.focus({preventScroll: true}); } catch (e) { /* gone */ } } }
  function openModal(cls, label, content) { closeModal(); closePops(0); modal.back = document.activeElement; const box = h('div', {class: 'hd-mbox ' + cls, role: 'dialog', 'aria-modal': 'true', 'aria-label': label}, content);
    modal.el = h('div', {class: 'hd-modal'}, box); modal.el.addEventListener('pointerdown', ev => { if (ev.target === modal.el) closeModal(); }); document.body.appendChild(modal.el); return box; }
  function palette() {
    const q = h('input', {class: 'hd-in hd-palq', type: 'text', placeholder: 'Type a command…', 'aria-label': 'Find a command', autocomplete: 'off', spellcheck: 'false'}), list = h('div', {class: 'hd-pallist', role: 'listbox', 'aria-label': 'Commands'}); let items = [], at = 0;
    function draw() { const s = q.value.trim().toLowerCase(), words = s.split(/\s+/).filter(Boolean); items = commands.filter(c => c.label && (!c.when || c.when()) && words.every(w => (c.label + ' ' + (c.group || '')).toLowerCase().indexOf(w) >= 0)).slice(0, 60); at = clamp(at, 0, Math.max(0, items.length - 1)); clear(list);
      items.forEach((c, i) => list.appendChild(h('button', {class: 'hd-mi' + (i === at ? ' cur' : ''), type: 'button', role: 'option', tabIndex: -1, 'aria-selected': String(i === at), on: {click: () => { closeModal(); runCmd(c); }, pointermove: () => { if (at !== i) { at = i; mark(); } }}}, h('span', {class: 'hd-mlab', text: c.label}), h('span', {class: 'hd-mgroup', text: c.group || ''}), c.keys ? h('span', {class: 'hd-mkeys', text: keysLabel(norm([].concat(c.keys)[0]))}) : null)));
      if (!items.length) list.appendChild(h('div', {class: 'hd-none pad', text: 'Nothing matches that.'})); }
    function mark() { Array.from(list.children).forEach((b, i) => { b.classList.toggle('cur', i === at); if (b.setAttribute) b.setAttribute('aria-selected', String(i === at)); if (i === at && b.scrollIntoView) b.scrollIntoView({block: 'nearest'}); }); }
    q.addEventListener('input', () => { at = 0; draw(); });
    q.addEventListener('keydown', ev => { ev.stopPropagation(); if (ev.key === 'ArrowDown') { ev.preventDefault(); at = Math.min(items.length - 1, at + 1); mark(); } else if (ev.key === 'ArrowUp') { ev.preventDefault(); at = Math.max(0, at - 1); mark(); } else if (ev.key === 'Enter') { ev.preventDefault(); const c = items[at]; closeModal(); if (c) runCmd(c); } else if (ev.key === 'Escape') { ev.preventDefault(); closeModal(); } });
    openModal('hd-pal', 'Find a command', [h('div', {class: 'hd-palhead'}, icon('search'), q), list]); draw(); q.focus();
  }
  function shortcutSheet() {
    const groups = {}; for (const c of commands) { if (!c.keys || !c.label) continue; (groups[c.group || 'Other'] = groups[c.group || 'Other'] || []).push(c); }
    const extra = {Edit: [['Copy', 'mod+c'], ['Cut', 'mod+x'], ['Paste', 'mod+v']], Canvas: [['Pan', 'space+drag'], ['Zoom', 'mod+scroll'], ['Select a layer inside a group', 'mod+click'], ['Go into a group / edit text', 'enter'], ['Select the parent', 'shift+enter'], ['Next layer', 'tab'], ['Duplicate while dragging', 'alt+drag'], ['Keep the proportions / snap the angle', 'shift+drag'], ['Switch snapping off while dragging', 'mod+drag']]};
    const cols = h('div', {class: 'hd-keycols'});
    for (const col of [['Tools', 'Edit'], ['Arrange'], ['View', 'Canvas', 'Other']]) { const c = h('div', {class: 'hd-keycol'});
      for (const g of col) { const list = (groups[g] || []).map(k => [k.label, norm([].concat(k.keys)[0])]).concat(extra[g] || []); if (!list.length) continue;
        c.appendChild(h('div', {class: 'hd-keygroup'}, h('h3', {text: g}), list.map(k => h('div', {class: 'hd-keyrow'}, h('span', {text: k[0]}), h('span', {class: 'hd-kbds'}, keyParts(k[1]).map(x => h('kbd', {text: x}))))))); }
      cols.appendChild(c); }
    const closeB = ibtn('close', 'Close', closeModal); openModal('hd-sheet', 'Keyboard shortcuts', [h('div', {class: 'hd-sheethead'}, h('h2', {text: 'Keyboard shortcuts'}), closeB), cols]); closeB.focus();
  }
  function defaultCommands() {
    const tool = (id, label, keys) => command({id: 'tool.' + id, label: label + ' tool', group: 'Tools', keys: keys, run: () => T().set(id)});
    tool('move', 'Move', 'v'); tool('frame', 'Frame', 'f'); tool('rect', 'Rectangle', 'r'); tool('ellipse', 'Ellipse', 'o'); tool('line', 'Line', 'l'); tool('polygon', 'Polygon'); tool('star', 'Star'); tool('pen', 'Pen', 'p'); tool('pencil', 'Pencil', 'shift+p'); tool('text', 'Text', 't'); tool('hand', 'Hand', 'h'); tool('comment', 'Comment', 'c'); tool('zoom', 'Zoom', 'z');
    const ed = (id, label, keys, run, group) => command({id: id, label: label, group: group || 'Edit', keys: keys, run: run, edit: true});
    ed('undo', 'Undo', 'mod+z', () => A().undo()); ed('redo', 'Redo', ['mod+shift+z', 'mod+y'], () => A().redo());
    ed('duplicate', 'Duplicate', 'mod+d', () => A().duplicate()); ed('delete', 'Delete', ['delete', 'backspace'], () => A().remove());
    command({id: 'selectAll', label: 'Select all', group: 'Edit', keys: 'mod+a', run: () => A().selectAll()}); command({id: 'selectInverse', label: 'Select the others', group: 'Edit', keys: 'mod+shift+a', run: () => A().selectInverse()});
    ed('rename', 'Rename the layer', 'mod+r', () => { const s = sel(); if (s.length === 1) renameLayer(s[0]); });
    ed('group', 'Group', 'mod+g', () => A().group(), 'Arrange'); ed('ungroup', 'Ungroup', ['mod+shift+g', 'mod+backspace'], () => A().ungroup(), 'Arrange'); ed('frameSel', 'Frame selection', 'mod+alt+g', () => A().frameSelection(), 'Arrange'); ed('autoLayout', 'Add auto layout', 'shift+a', addAutoLayout, 'Arrange');
    ed('front', 'Bring to front', ']', () => A().order('front'), 'Arrange'); ed('back', 'Send to back', '[', () => A().order('back'), 'Arrange'); ed('forward', 'Bring forward', 'mod+]', () => A().order('forward'), 'Arrange'); ed('backward', 'Send backward', 'mod+[', () => A().order('backward'), 'Arrange');
    ed('lock', 'Lock or unlock', 'mod+shift+l', () => A().toggle('locked'), 'Arrange'); ed('hide', 'Show or hide', 'mod+shift+h', () => A().toggle('visible'), 'Arrange');
    ed('alignLeft', 'Align left', 'alt+a', () => A().align('left'), 'Arrange'); ed('alignHCenter', 'Align centre', 'alt+h', () => A().align('hcenter'), 'Arrange'); ed('alignRight', 'Align right', 'alt+d', () => A().align('right'), 'Arrange');
    ed('alignTop', 'Align top', 'alt+w', () => A().align('top'), 'Arrange'); ed('alignVCenter', 'Align middle', 'alt+v', () => A().align('vcenter'), 'Arrange'); ed('alignBottom', 'Align bottom', 'alt+s', () => A().align('bottom'), 'Arrange');
    ed('distH', 'Distribute horizontally', 'mod+alt+h', () => A().distribute('h'), 'Arrange'); ed('distV', 'Distribute vertically', 'mod+alt+v', () => A().distribute('v'), 'Arrange'); ed('tidy', 'Tidy up', 'mod+alt+t', () => A().tidy(), 'Arrange');
    ed('flipH', 'Flip horizontal', 'shift+h', () => A().flip('h'), 'Arrange'); ed('flipV', 'Flip vertical', 'shift+v', () => A().flip('v'), 'Arrange');
    const vw = (id, label, keys, run) => command({id: id, label: label, group: 'View', keys: keys, run: run});
    vw('zoomFit', 'Zoom to fit', 'shift+1', () => T().view.fit()); vw('zoomSel', 'Zoom to selection', 'shift+2', () => A().zoomSelection()); vw('zoomIn', 'Zoom in', ['+', '=', 'shift+='], () => T().view.zoomBy(1.5)); vw('zoomOut', 'Zoom out', '-', () => T().view.zoomBy(1 / 1.5)); vw('zoom100', 'Zoom to 100%', ['0', 'shift+0'], () => T().view.zoomTo(1, true));
    vw('toggleUI', 'Show or hide the panels', 'mod+\\', toggleUI); vw('palette', 'Find a command', ['mod+k', 'mod+/'], palette); vw('shortcuts', 'Keyboard shortcuts', ['shift+/', '?'], shortcutSheet);
    vw('themeLight', 'Light theme', null, () => { if (window.HoolaTheme) window.HoolaTheme.setTheme('light'); }); vw('themeDark', 'Dark theme', null, () => { if (window.HoolaTheme) window.HoolaTheme.setTheme('dark'); });
    command({id: 'export', label: 'Export…', group: 'Other', keys: 'mod+shift+e', run: () => fire('export', sel())}); command({id: 'share', label: 'Share this file', group: 'Other', run: () => fire('share', HD.app.file)}); command({id: 'present', label: 'Present', group: 'Other', run: () => fire('present', presentStart())});
    command({id: 'ai', label: 'Ask Hoola to design…', group: 'Other', edit: true, run: () => { const c = T().view.centre(), w = HD.render.screenToWorld(c[0], c[1]); fire('ai', {page: HD.sel.page, x: Math.round(w[0]), y: Math.round(w[1])}); }});
    command({id: 'versions', label: 'Version history', group: 'Other', run: () => fire('versions', HD.app.file)}); command({id: 'addPage', label: 'Add a page', group: 'Other', edit: true, run: addPage}); command({id: 'files', label: 'Back to your files', group: 'Other', run: () => { location.hash = '#/'; }});
    for (const p of PRESETS) if (!p.head) command({id: 'frame.' + p[0], label: 'New frame: ' + p[0] + ' (' + p[1] + ' × ' + p[2] + ')', group: 'Frames', edit: true, run: () => A().addFrame(p[1], p[2], p[0])});
  }

  /* ---------------------------------------------------------------- keyboard + clipboard */
  function onKey(ev) {
    if (!ui.mounted) return;
    if (modal.el) { if (ev.key === 'Escape') { ev.preventDefault(); closeModal(); } else if (ev.key === 'Tab') { const f = modal.el.querySelectorAll('button, input'); if (f.length && !modal.el.contains(document.activeElement)) { ev.preventDefault(); f[0].focus(); } } return; }
    if (pops.length && ev.key === 'Escape') { ev.preventDefault(); closePops(pops.length - 1); return; }
    if (typing(ev)) return;
    if (ev.target && ev.target.closest && ev.target.closest('.hd-pop') && (ev.key === 'Enter' || ev.key === ' ' || /^Arrow|^Home$|^End$|^Tab$/.test(ev.key))) return;
    if ((ev.key === 'Enter' || ev.key === ' ') && ev.target && ev.target.tagName === 'BUTTON') return;
    if (ev.key === 'Tab' && ev.target !== T().canvas) return;
    for (const c of combosOf(ev)) { const s = shortcuts[c]; if (s) { ev.preventDefault(); closePops(0); try { s.fn(ev); } catch (e) { toast(e.message || String(e), true); } return; } }
    if (T().key(ev)) ev.preventDefault();
  }
  function editorFocus(ev) { return ui.mounted && !modal.el && !typing(ev); }
  function onCopy(ev) { const ws = window.getSelection ? window.getSelection() : null; if (!editorFocus(ev) || (ws && !ws.isCollapsed && String(ws).trim())) return; const sig = A().clipText(); if (!sig) return; ev.clipboardData.setData('text/plain', sig); ev.preventDefault(); if (ev.type === 'cut') { if (U().canEdit()) A().remove(); } }
  function imageSize(blob) { return new Promise(resolve => { const url = URL.createObjectURL(blob), img = new Image(); img.onload = () => { resolve([img.naturalWidth || 200, img.naturalHeight || 200]); URL.revokeObjectURL(url); }; img.onerror = () => { resolve([200, 200]); URL.revokeObjectURL(url); }; img.src = url; }); }
  async function placeImage(blob, name, at) { const size = await imageSize(blob), hash = await uploadImage(blob); if (!hash) return null; let w = size[0], hh = size[1]; const k = Math.min(1, 1600 / Math.max(w, hh)); w *= k; hh *= k; return A().pasteImage(hash, w, hh, name || 'Image', at); }
  function onPaste(ev) {
    if (!editorFocus(ev)) return; const cd = ev.clipboardData; if (!cd) return; ev.preventDefault(); if (!U().canEdit()) { toast('This file is view only.'); return; }
    const files = Array.from(cd.files || []).filter(f => /^image\//.test(f.type)); if (files.length) { files.slice(0, 6).forEach(f => { placeImage(f, (f.name || 'Image').replace(/\.[a-z0-9]+$/i, '')); }); return; }
    const text = cd.getData('text/plain') || '', clip = A().clip();
    if (/^\s*(<\?xml[^>]*>\s*)?(<!--[\s\S]*?-->\s*)?<svg[\s>]/i.test(text)) { if (hooks.importSvg) { const c = T().view.centre(), w = HD.render.screenToWorld(c[0], c[1]); fire('importSvg', text, {x: w[0], y: w[1], page: HD.sel.page}); } else placeImage(new Blob([text], {type: 'image/svg+xml'}), 'SVG'); return; }
    if (clip && (!text || text === clip.sig)) { A().paste(); return; }
    if (text.trim()) A().pasteText(text); else if (clip) A().paste();
  }
  function onDrop(ev) { if (!ui.mounted || !ev.dataTransfer) return; const files = Array.from(ev.dataTransfer.files || []).filter(f => /^image\//.test(f.type)); if (!files.length) return; ev.preventDefault(); if (!U().canEdit()) return; const r = T().canvas.getBoundingClientRect(), w = HD.render.screenToWorld(ev.clientX - r.left, ev.clientY - r.top);
    files.slice(0, 6).forEach((f, i) => placeImage(f, (f.name || 'Image').replace(/\.[a-z0-9]+$/i, ''), [w[0] + i * 24, w[1] + i * 24])); }

  /* ---------------------------------------------------------------- the shell */
  function tabs(side) {
    const list = [{id: side === 'left' ? 'layers' : 'design', title: side === 'left' ? 'Layers' : 'Design'}].concat(ui.panels[side].filter(p => !p.when || p.when())), key = side === 'left' ? 'leftTab' : 'rightTab';
    if (!list.some(p => p.id === ui[key])) ui[key] = list[0].id; const el = side === 'left' ? ui.leftTabs : ui.rightTabs, sig = list.map(p => p.id).join() + '#' + ui[key]; if (el.dataset.sig === sig) return list; el.dataset.sig = sig; clear(el);
    for (const p of list) el.appendChild(h('button', {class: 'hd-tab' + (p.id === ui[key] ? ' on' : ''), type: 'button', role: 'tab', 'aria-selected': String(p.id === ui[key]), text: p.title, on: {click: () => { ui[key] = p.id; ui.sig = ''; ui.customSig = ''; closePops(0); refresh(); }}}));
    return list;
  }
  function paintAll() {
    if (!ui.mounted) return; syncTop();
    const lt = tabs('left'); ui.layersBody.hidden = ui.leftTab !== 'layers'; ui.leftCustom.hidden = ui.leftTab === 'layers';
    if (ui.leftTab === 'layers') { pagesPaint(); layersPaint(); } else custom(ui.leftCustom, lt.find(p => p.id === ui.leftTab), 'L');
    const rt = tabs('right'); ui.designBody.hidden = ui.rightTab !== 'design'; ui.rightCustom.hidden = ui.rightTab === 'design';
    if (ui.rightTab === 'design') designPaint(ui.designBody); else custom(ui.rightCustom, rt.find(p => p.id === ui.rightTab), 'R');
    syncBanner();
  }
  function custom(el, p, side) { if (!p || !p.render) return; const key = side + p.id; if (el.dataset.panel !== key) { clear(el); el.dataset.panel = key; } try { p.render(el); } catch (e) { clear(el).appendChild(h('p', {class: 'hd-note pad', text: 'This panel could not be shown.'})); if (window.console) console.error(e); } }
  function registerPanel(side, id, def) { const list = ui.panels[side === 'left' ? 'left' : 'right'], i = list.findIndex(p => p.id === id), p = Object.assign({id: id, title: id}, def); if (i >= 0) list[i] = p; else list.push(p); if (side === 'left') { if (ui.leftTabs) ui.leftTabs.dataset.sig = ''; } else if (ui.rightTabs) ui.rightTabs.dataset.sig = ''; refresh(); }
  function syncBanner() {
    if (!ui.banner) return; const st = (HD.net && HD.net.status) || 'offline', view = !U().canEdit() && st === 'live'; let text = '', cls = '';
    if (T().panOnly) { text = 'This screen is small: you can look around here. Open Hoola Design on a bigger screen to edit.'; cls = 'info'; }
    else if (st === 'offline-full') { text = 'You are offline and many changes are waiting. Editing is paused until the connection is back.'; cls = 'bad'; }
    else if (st === 'offline') { text = 'You are offline. Changes are kept here and saved when the connection is back.'; cls = 'warn'; }
    else if (st === 'connecting' && ui.wasLive) { text = 'Reconnecting…'; cls = 'warn'; }
    else if (view) { text = 'View only. You can look around, select and copy, but not change this file.'; cls = 'info'; }
    if (st === 'live') ui.wasLive = true;
    if (ui.banner.dataset.t !== text) { ui.banner.dataset.t = text; ui.banner.textContent = text; ui.banner.className = 'hd-banner ' + cls; ui.banner.hidden = !text; }
  }
  function sizeMode() { const small = innerWidth < 760; if (ui.root) ui.root.classList.toggle('hd-small', small); if (T().panOnly !== small) { T().panOnly = small; T().set(small ? 'hand' : 'move'); refresh(); } }
  const offs = [];
  function mount(rootEl) {
    if (ui.mounted) unmount(); ui.root = rootEl; clear(rootEl); rootEl.classList.add('hd-editor'); ui.sig = ''; ui.syncs = []; Pg.sig = ''; L.dirty = true; L.expanded = new Set(); L.editing = null; Pg.editing = null; peopleSig = ''; zoomShown = 0; ui.wasLive = false; ui.pageViews = {};
    ui.leftTabs = h('div', {class: 'hd-tabs', role: 'tablist', 'aria-label': 'Left panel'}); ui.rightTabs = h('div', {class: 'hd-tabs', role: 'tablist', 'aria-label': 'Right panel'});
    ui.layersBody = h('div', {class: 'hd-pbody layers'}, pagesBuild(), layersBuild()); ui.leftCustom = h('div', {class: 'hd-pbody custom', hidden: true});
    ui.designBody = h('div', {class: 'hd-pbody design'}); ui.rightCustom = h('div', {class: 'hd-pbody custom', hidden: true});
    ui.canvas = h('canvas', {class: 'hd-canvas', tabIndex: 0, 'aria-label': 'Design canvas. Press ? for the keyboard shortcuts.'}); ui.banner = h('div', {class: 'hd-banner', role: 'status', hidden: true});
    ui.stage = h('main', {class: 'hd-stage'}, ui.canvas, ui.banner);
    add(rootEl, [buildTop(), h('div', {class: 'hd-body'}, h('aside', {class: 'hd-left', 'aria-label': 'Pages and layers'}, ui.leftTabs, ui.layersBody, ui.leftCustom), ui.stage, h('aside', {class: 'hd-right', 'aria-label': 'Properties'}, ui.rightTabs, ui.designBody, ui.rightCustom))]);
    HD.render.init(ui.canvas); T().attach(ui.canvas, ui.stage); ui.mounted = true;
    if (!ui.wired) { ui.wired = true;
      HD.store.on('change', ch => { if (!ch || ch.structural !== false) L.dirty = true; refresh(); }); HD.store.on('load', () => { L.dirty = true; Pg.sig = ''; ui.sig = ''; refresh(); });
      HD.sel.on('change', () => { if (pops.length) closePops(0); onSelChange(); }); T().onChange(() => { syncTools(); }); T().onView(syncZoom); HD.render.addOverlay(() => syncZoom());
      if (HD.net && HD.net.on) { HD.net.on('status', () => { syncNet(); syncBanner(); refresh(); }); HD.net.on('presence', ev => { if (!ev || ev.type !== 'pres') syncNet(); }); HD.net.on('pending', () => syncNet()); HD.net.on('file', f => { if (f && HD.app && HD.app.file && f.name) { HD.app.file.name = f.name; syncTop(); } }); }
      window.addEventListener('keydown', onKey); document.addEventListener('copy', onCopy); document.addEventListener('cut', onCopy); document.addEventListener('paste', onPaste);
      window.addEventListener('resize', sizeMode); window.addEventListener('dragover', ev => { if (ui.mounted && ev.dataTransfer && Array.from(ev.dataTransfer.types || []).indexOf('Files') >= 0) ev.preventDefault(); }); window.addEventListener('drop', onDrop);
      if (window.HoolaTheme) window.HoolaTheme.onChange(() => { if (ui.mounted) HD.render.invalidate(); });
      }
    sizeMode(); paintAll(); ui.canvas.focus({preventScroll: true});
  }
  function unmount() { if (!ui.mounted) return; closePops(0); closeModal(); if (T().text && T().text.el) T().text.commit(); ui.mounted = false; if (ui.root) { clear(ui.root); ui.root.classList.remove('hd-editor', 'hd-noui', 'hd-small'); } ui.root = null; for (const f of offs.splice(0)) f(); }

  /* The built-in commands exist from load, BEFORE any feature file adds its own: a feature file that calls
     HD.ui.command() while loading used to leave the editor without every default shortcut (the old test was
     "no command yet"), and a feature's shortcut now wins over a default on the same keys. */
  defaultCommands();

  HD.ui = {
    mount: mount, unmount: unmount, toast: toast, refresh: refresh, api: api, esc: esc,
    registerPanel: registerPanel, registerMenu: registerMenu, registerShortcut: registerShortcut, command: command, run: runCmd,
    hook: hook, fire: fire, hooks: hooks, designSection: designSection, contextMenu: contextMenu, menu: menu, pop: pop, closePops: closePops, palette: palette, shortcuts: shortcutSheet,
    icon: icon, h: h, clear: clear, numField: numField, select: select, seg: seg, section: section, row: row, colorLine: colorLine, paintPicker: paintPicker,
    loadFont: loadFont, fonts: FONTS, setPage: setPage, renameLayer: renameLayer, revealLayers(ids) { reveal([].concat(ids)); layersPaint(); }, uploadImage: uploadImage, keysLabel: keysLabel, modal: openModal, closeModal: closeModal, MIXED: MIXED,
    get token() { return TOKEN; }, get mounted() { return ui.mounted; }, state: ui
  };
})();

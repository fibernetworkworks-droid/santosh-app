/* v0.825 Hoola App Engine - the preview helper (served ONLY inside the Studio's preview, never on a live app).
   1. Error collector: page errors, unhandled promise rejections and console.error go to the Studio (postMessage);
      the server maps them to the app's own file and line through the build's hidden source map.
   2. Select: the Studio switches it on; hover outlines the element, a click sends its source tag (data-hs) instead of
      running the app's own click. Esc switches it off.
   3. Live style / words: the Studio sends what the style panel shows; it is drawn at once on every element that came
      from the same line (no build, nothing saved) until the real change is built. */
(() => {
  'use strict';
  if (window.parent === window) return;
  const post = m => { try { window.parent.postMessage(Object.assign({hoola: 'ae'}, m), '*'); } catch (e) { /* no parent */ } };
  // v0.999.64 D3: a pre-rendered site page has no app script, so the helper tells the shell which page is open
  try {
    const b = new URL(document.baseURI).pathname;
    const here = location.pathname.startsWith(b) ? '/' + location.pathname.slice(b.length) : location.pathname;
    window.parent.postMessage({hoola: 'nav', path: here + location.search}, '*');
  } catch (e) { /* no base */ }
  const sent = new Set();
  let count = 0;
  function report(kind, msg, stack) {
    const m = String(msg || '').slice(0, 500);
    const key = kind + '|' + m;
    if (!m || sent.has(key) || count > 30) return;
    sent.add(key); count += 1;
    post({t: 'err', kind, m, s: String(stack || '').slice(0, 4000), p: location.pathname.split('/').slice(-1)[0] || '/'});
  }
  addEventListener('error', e => { if (e.error || e.message) report('page', e.message || String(e.error), e.error && e.error.stack); });
  addEventListener('unhandledrejection', e => { const r = e.reason; report('promise', (r && r.message) || String(r), r && r.stack); });
  // v0.999.324 (the Dyad read): the app's console and its network calls, for Hoola to read (app_engine action=read_logs).
  // Bounded: 20 arguments, 8 KB an argument, 64 KB a line, objects 6 deep / 50 keys, 400 lines a page load. Network =
  // method, path, status, time - never a body, never a query value (only the names), never a header.
  let logs = 0;
  const seen = new WeakSet();
  function show(x, depth) {
    if (x === null || x === undefined || typeof x !== 'object') return typeof x === 'string' ? x : String(x);
    if (x instanceof Error) return (x.name || 'Error') + ': ' + x.message;
    if (depth > 6 || seen.has(x)) return '[...]';
    seen.add(x);
    try {
      if (Array.isArray(x)) return '[' + x.slice(0, 50).map(v => show(v, depth + 1)).join(', ') + (x.length > 50 ? ', ...' : '') + ']';
      if (typeof Element !== 'undefined' && x instanceof Element) return '<' + x.tagName.toLowerCase() + '>';
      const ks = Object.keys(x);
      return '{' + ks.slice(0, 50).map(k => k + ': ' + show(x[k], depth + 1)).join(', ') + (ks.length > 50 ? ', ...' : '') + '}';
    } catch (e) { return '[object]'; }
  }
  function log(level, args) {
    if (logs >= 400) return;
    logs += 1;
    try {
      const text = [...args].slice(0, 20).map(a => show(a, 0).slice(0, 8192)).join(' ').slice(0, 65536);
      post({t: 'log', l: level, a: text, p: location.pathname.split('/').slice(-1)[0] || '/'});
    } catch (e) { /* never break the app */ }
  }
  for (const level of ['log', 'info', 'warn', 'error', 'debug']) {
    const orig = console[level];
    console[level] = function (...a) {
      if (level === 'error') {
        try { const err = a.find(x => x instanceof Error); report('console', a.map(x => (x && x.message) || String(x)).join(' ').slice(0, 500), err && err.stack); } catch (e) { /* never break the app */ }
      }
      log(level, a);
      return orig.apply(this, a);
    };
  }
  function where(u) {
    try {
      const x = new URL(String(u), location.href);
      const q = [...x.searchParams.keys()].slice(0, 12);
      return (x.origin === location.origin ? '' : x.origin) + x.pathname + (q.length ? '?' + q.join('&') : '');
    } catch (e) { return String(u).split('?')[0].slice(0, 300); }
  }
  function net(method, url, status, t0, err) {
    if (logs >= 400) return;
    logs += 1;
    post({t: 'net', m: String(method || 'GET').toUpperCase().slice(0, 8), u: where(url).slice(0, 400), s: status || 0,
      ms: Math.round(performance.now() - t0), e: err ? String(err).slice(0, 200) : ''});
  }
  if (window.fetch) {
    const of = window.fetch;
    window.fetch = function (input, init) {
      const t0 = performance.now();
      const url = input && typeof input === 'object' && 'url' in input ? input.url : input;
      const method = (init && init.method) || (input && typeof input === 'object' && input.method) || 'GET';
      return of.apply(this, arguments).then(r => { net(method, url, r.status, t0); return r; },
        e => { net(method, url, 0, t0, e && e.message); throw e; });
    };
  }
  if (window.XMLHttpRequest) {
    const oo = XMLHttpRequest.prototype.open, os = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function (m, u) { this.__h = {m, u}; return oo.apply(this, arguments); };
    XMLHttpRequest.prototype.send = function () {
      const h = this.__h || {}, t0 = performance.now();
      this.addEventListener('loadend', () => net(h.m, h.u, this.status, t0, this.status ? '' : 'no answer'));
      return os.apply(this, arguments);
    };
  }

  let mode = 'off', box = null, tip = null, hot = null;
  const tagOf = el => el && el.closest ? el.closest('[data-hs]') : null;
  function draw(el) {
    if (!box) {
      box = document.createElement('div'); tip = document.createElement('div');
      box.setAttribute('data-hoola-ui', '');
      box.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483646;border:2px solid #6d4aff;border-radius:4px;background:rgba(109,74,255,.08);transition:all .06s';
      tip.style.cssText = 'position:fixed;pointer-events:none;z-index:2147483647;background:#17161c;color:#fff;font:12px/1.4 ui-sans-serif,system-ui;padding:3px 7px;border-radius:6px;white-space:nowrap';
      document.documentElement.append(box, tip);
    }
    if (!el) { box.style.display = tip.style.display = 'none'; return; }
    const r = el.getBoundingClientRect();
    Object.assign(box.style, {display: 'block', left: r.left - 2 + 'px', top: r.top - 2 + 'px', width: r.width + 4 + 'px', height: r.height + 4 + 'px'});
    const hs = el.getAttribute('data-hs') || '';
    tip.textContent = '<' + el.tagName.toLowerCase() + '> ' + (el.getAttribute('data-hc') ? el.getAttribute('data-hc') + ' · ' : '') + hs.replace(/:\d+$/, '');
    Object.assign(tip.style, {display: 'block', left: Math.max(4, r.left) + 'px', top: Math.max(4, r.top - 24) + 'px'});
  }
  // v0.999.76 D7: on a React WEBSITE the Studio edits by section: the section's box (data-sec) + the words clicked
  const secOf = el => { const w = el && el.closest ? el.closest('[data-sec]') : null; return w && w.firstElementChild ? w : null; };
  // v0.999.130: a picture of the section (her photo, or the design's stand-in) - what she clicked to change it
  const picOf = (el, w) => { const p = el && el.closest ? el.closest('img,[role="img"]') : null; return p && w && w.contains(p) ? p : null; };
  const wordsAt = el => { let x = el; while (x && x !== document.body && !(x.innerText || '').trim()) x = x.parentElement; return x; };
  addEventListener('mousemove', e => {
    if (mode === 'site') { const w = secOf(e.target), pic = picOf(e.target, w); draw(pic || (w ? w.firstElementChild : null)); if (w && tip) tip.textContent = pic ? 'Picture in section ' + w.getAttribute('data-sec') + ' - click to change it' : 'Section ' + w.getAttribute('data-sec') + ' - click words or a picture to change them'; return; }
    if (mode !== 'select') return; hot = tagOf(e.target); draw(hot); }, true);
  addEventListener('click', e => {
    if (mode !== 'site') return;
    e.preventDefault(); e.stopPropagation();
    const w = secOf(e.target); if (!w) return;
    const pic = picOf(e.target, w);
    if (pic) {
      const all = [...w.querySelectorAll('img,[role="img"]')];
      post({t: 'sec-pick', sec: w.getAttribute('data-sec'), block: w.firstElementChild.getAttribute('data-block') || '',
        variant: w.firstElementChild.getAttribute('data-variant') || '', tag: 'img', text: '', leaf: false,
        pic: {src: pic.tagName === 'IMG' ? (pic.getAttribute('src') || '') : '', alt: (pic.getAttribute('alt') || pic.getAttribute('aria-label') || '').slice(0, 200), n: all.indexOf(pic)}});
      return;
    }
    const el = wordsAt(e.target);
    const leaf = el && [...el.childNodes].every(n => n.nodeType === 3);
    post({t: 'sec-pick', sec: w.getAttribute('data-sec'), block: w.firstElementChild.getAttribute('data-block') || '',
      variant: w.firstElementChild.getAttribute('data-variant') || '', tag: el ? el.tagName.toLowerCase() : '',
      text: el ? (el.innerText || '').trim().slice(0, 600) : '', leaf: !!leaf});
  }, true);
  addEventListener('click', e => {
    if (mode !== 'select') return;
    const el = tagOf(e.target);
    e.preventDefault(); e.stopPropagation();
    if (!el) return;
    const hs = el.getAttribute('data-hs');
    const kids = [...el.childNodes];
    post({t: 'pick', hs, hc: el.getAttribute('data-hc') || '', tag: el.tagName.toLowerCase(),
      text: (el.innerText || '').trim().slice(0, 120), cls: (el.getAttribute('class') || '').slice(0, 400),
      leaf: kids.every(n => n.nodeType === 3), same: document.querySelectorAll('[data-hs="' + hs + '"]').length});
  }, true);
  addEventListener('keydown', e => { if (e.key === 'Escape' && (mode === 'select' || mode === 'site')) { mode = 'off'; draw(null); post({t: 'mode', mode}); } }, true);

  const touched = new Map();
  function each(hs, fn) { document.querySelectorAll('[data-hs="' + String(hs).replace(/"/g, '') + '"]').forEach(fn); }
  addEventListener('message', e => {
    if (e.source !== window.parent) return;
    const d = e.data || {};
    if (d.hoola !== 'ae-cmd') return;
    if (d.t === 'mode') { mode = d.mode === 'select' ? 'select' : d.mode === 'site' ? 'site' : 'off'; if (mode === 'off') draw(null); document.documentElement.style.cursor = mode === 'off' ? '' : (mode === 'site' ? 'text' : 'crosshair'); }
    if (d.t === 'sec-text' && d.sec) {               // v0.999.76 D7: her new words shown at once, until the build lands
      const w = document.querySelector('[data-sec="' + String(d.sec).replace(/"/g, '') + '"]');
      const want = String(d.old || '').replace(/\s+/g, ' ').trim();
      if (w && want) {
        const walk = document.createTreeWalker(w, NodeFilter.SHOW_TEXT);
        for (let n = walk.nextNode(); n; n = walk.nextNode()) {
          const t = n.nodeValue.replace(/\s+/g, ' ').trim();
          if (t === want) { n.nodeValue = String(d.new || ''); break; }
          if (t.includes(want)) { n.nodeValue = n.nodeValue.replace(want, String(d.new || '')); break; }
        }
      }
    }
    if (d.t === 'style' && d.hs) {
      each(d.hs, el => {
        if (!touched.has(el)) touched.set(el, {style: el.getAttribute('style'), text: el.childNodes.length === 1 && el.firstChild.nodeType === 3 ? el.textContent : null});
        for (const [k, v] of Object.entries(d.css || {})) el.style.setProperty(k, v || '');
        if (typeof d.text === 'string' && touched.get(el).text !== null) el.textContent = d.text;
      });
    }
    if (d.t === 'clear') {
      touched.forEach((o, el) => { if (o.style === null) el.removeAttribute('style'); else el.setAttribute('style', o.style); if (o.text !== null) el.textContent = o.text; });
      touched.clear();
    }
  });
  post({t: 'ready', path: location.pathname});
})();

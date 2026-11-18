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
  const ce = console.error;
  console.error = function (...a) {
    try { const err = a.find(x => x instanceof Error); report('console', a.map(x => (x && x.message) || String(x)).join(' ').slice(0, 500), err && err.stack); } catch (e) { /* never break the app */ }
    return ce.apply(this, a);
  };

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
  addEventListener('mousemove', e => { if (mode !== 'select') return; hot = tagOf(e.target); draw(hot); }, true);
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
  addEventListener('keydown', e => { if (e.key === 'Escape' && mode === 'select') { mode = 'off'; draw(null); post({t: 'mode', mode}); } }, true);

  const touched = new Map();
  function each(hs, fn) { document.querySelectorAll('[data-hs="' + String(hs).replace(/"/g, '') + '"]').forEach(fn); }
  addEventListener('message', e => {
    if (e.source !== window.parent) return;
    const d = e.data || {};
    if (d.hoola !== 'ae-cmd') return;
    if (d.t === 'mode') { mode = d.mode === 'select' ? 'select' : 'off'; if (mode === 'off') draw(null); document.documentElement.style.cursor = mode === 'select' ? 'crosshair' : ''; }
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

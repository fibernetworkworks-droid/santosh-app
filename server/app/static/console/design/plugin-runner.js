/* HOOLA DESIGN - D8a plugin RUNNER (docs/HOOLA_DESIGN_PLAN.md section 8, D8a). NOT loaded by the editor.
   The server inlines this file into GET /api/design/plugin-frame (design/plugins.py frame_page) and allows it by its
   sha256 hash. That page lives in <iframe sandbox="allow-scripts"> with an OPAQUE origin and its own CSP
   (connect-src 'none', no 'unsafe-eval', worker-src blob:). This script is the only script of that page.

   What it does:
   - says {t:'ready'} to the editor (window.parent) as soon as it loads;
   - on {t:'start', code, command, manifest} builds ONE Web Worker from a blob = the `hoola` API prelude + the plugin's
     code, so the plugin never runs in this document (no DOM, no RTCPeerConnection, nothing to escape through) and a
     plugin stuck in a loop blocks only its own worker thread - the editor removes this iframe, which ends the worker;
   - relays: worker {t:'call', id, m, a} -> editor; editor {t:'res', id, ok, v | err} -> worker; editor {t:'ping'}
     -> worker -> {t:'pong'} -> editor (the editor's watchdog); worker {t:'done' | 'idle' | 'fail'} -> editor;
   - hoola.ui.show(html): once the editor allowed it (its 'res' is ok), the html is drawn INTO this page after it is
     cleaned (scripts, frames, objects, forms, meta / base / link, event attributes and outside links removed; the CSP
     would stop them anyway). A click on an element with data-action, or a change of one, is sent to the worker as
     {t:'ui', action, values: {name: value of every named field}}.
   Every message to the editor is a JSON STRING (the editor checks its size and shape before it parses it); the
   editor answers with JSON strings too. Nothing here is trusted by the editor: it checks every call again. */
(function () {
  'use strict';
  var host = window.parent;
  var worker = null, started = false, pending = Object.create(null), PRE = 0;
  var box = document.getElementById('hp-ui');

  function toHost(obj) { try { host.postMessage(JSON.stringify(obj), '*'); } catch (e) { /* the editor is gone */ } }
  function toWorker(obj) { if (worker) worker.postMessage(obj); }

  /* the hoola API as the plugin sees it (inside the worker). Built as text: it becomes the head of the worker's blob. */
  function prelude(command, manifest) {
    return [
      '"use strict";',
      'var __hp = {n: 0, wait: Object.create(null), ui: [], closed: false};',
      'function __call(m, a) { return new Promise(function (res, rej) { var id = ++__hp.n; __hp.wait[id] = {res: res, rej: rej}; postMessage({t: "call", id: id, m: m, a: a}); }); }',
      'self.onmessage = function (e) { var d = e.data; if (!d || typeof d !== "object") return;',
      '  if (d.t === "res") { var w = __hp.wait[d.id]; if (!w) return; delete __hp.wait[d.id]; if (d.ok) w.res(d.v); else w.rej(new Error(String(d.err || "Refused"))); }',
      '  else if (d.t === "ping") postMessage({t: "pong", s: d.s});',
      '  else if (d.t === "ui") { for (var i = 0; i < __hp.ui.length; i++) { try { var r = __hp.ui[i](d.msg); if (r && r.then) r.then(null, __fail); } catch (err) { __fail(err); } } } };',
      'function __fail(err) { postMessage({t: "fail", error: String((err && err.message) || err), stack: String((err && err.stack) || "").slice(0, 2000)}); }',
      'self.addEventListener("error", function (ev) { ev.preventDefault(); __fail(ev.error || ev.message); });',
      'self.addEventListener("unhandledrejection", function (ev) { ev.preventDefault(); __fail(ev.reason); });',
      'function __fetched(r) { if (r && typeof r === "object") { r.text = function () { return r.encoding === "text" ? r.body : atob(r.body); }; r.json = function () { return JSON.parse(r.text()); }; } return r; }',
      'var hoola = Object.freeze({',
      '  command: ' + JSON.stringify(command) + ', manifest: Object.freeze(' + JSON.stringify(manifest) + '),',
      '  selection: function () { return __call("selection", []); },',
      '  select: function (ids) { return __call("select", [ids]); },',
      '  get: function (id) { return __call("get", [id]); },',
      '  children: function (id) { return __call("children", [id]); },',
      '  page: function () { return __call("page", []); },',
      '  pages: function () { return __call("pages", []); },',
      '  find: function (q) { return __call("find", [q || {}]); },',
      '  create: function (type, parent, props) { return __call("create", [type, parent, props || {}]); },',
      '  set: function (id, props) { return __call("set", [id, props || {}]); },',
      '  remove: function (ids) { return __call("remove", [ids]); },',
      '  move: function (ids, parent, before) { return __call("move", [ids, parent, before === undefined ? null : before]); },',
      '  notify: function (text) { return __call("notify", [String(text)]); },',
      '  exportPNG: function (id, scale) { return __call("exportPNG", [id, scale === undefined ? 1 : scale]); },',
      '  exportSVG: function (id) { return __call("exportSVG", [id]); },',
      '  fetch: function (url, opts) { return __call("fetch", [url, opts || {}]).then(__fetched); },',
      '  storage: Object.freeze({ get: function (k) { return __call("storage.get", [k]); }, set: function (k, v) { return __call("storage.set", [k, v === undefined ? null : v]); }, keys: function () { return __call("storage.keys", []); } }),',
      '  ui: Object.freeze({ show: function (html, opts) { return __call("ui.show", [String(html), opts || {}]); }, on: function (fn) { if (typeof fn === "function") __hp.ui.push(fn); }, close: function () { return __call("close", []); } }),',
      '  close: function () { __hp.closed = true; return __call("close", []); }',
      '});',
      'self.hoola = hoola;',
      '(async function (hoola, command) {'
    ].join('\n');
  }
  var TAIL = '\n}).call(undefined, hoola, hoola.command).then(function () { postMessage({t: "end"}); }, __fail);\n';

  function start(d) {
    if (started) return;
    started = true;
    var code = String(d.code || ''), head = prelude(String(d.command || ''), d.manifest || {});
    PRE = head.split('\n').length;                 /* the plugin's line 1 is the worker's line PRE + 1 */
    var url = '';
    try {
      url = URL.createObjectURL(new Blob([head + '\n' + code + TAIL], {type: 'text/javascript'}));
      worker = new Worker(url);
    } catch (e) { toHost({t: 'fail', error: 'The plugin could not start: ' + String(e && e.message || e)}); return; }
    worker.onmessage = function (e) { fromWorker(e.data); };
    worker.onerror = function (ev) {                 /* a syntax error (the code never ran) or an error the worker did not catch */
      if (ev && ev.preventDefault) ev.preventDefault();
      var line = ev && ev.lineno ? ev.lineno - PRE : 0;
      toHost({t: 'fail', error: String((ev && ev.message) || 'The plugin stopped with an error.'), line: line > 0 ? line : 0});
    };
    setTimeout(function () { try { URL.revokeObjectURL(url); } catch (e) { /* fine */ } }, 4000);
  }

  function fromWorker(d) {
    if (!d || typeof d !== 'object') return;
    if (d.t === 'call') {
      var id = +d.id, m = String(d.m || '');
      if (!(id > 0)) return;
      pending[id] = {m: m, a: d.a};
      var text;
      try { text = JSON.stringify({t: 'call', id: id, m: m, a: d.a === undefined ? [] : d.a}); }
      catch (e) { delete pending[id]; toWorker({t: 'res', id: id, ok: false, err: 'Those arguments can not be sent (they must be plain data).'}); return; }
      try { host.postMessage(text, '*'); } catch (e) { /* gone */ }
    } else if (d.t === 'pong') toHost({t: 'pong', s: d.s});
    else if (d.t === 'end') toHost({t: 'end'});
    else if (d.t === 'fail') toHost({t: 'fail', error: String(d.error || '').slice(0, 2000), line: lineOf(String(d.stack || ''))});
  }
  function lineOf(stack) { var m = /blob:[^\s)]*:(\d+):\d+/.exec(stack); if (!m) return 0; var n = +m[1] - PRE; return n > 0 ? n : 0; }

  /* ---------------------------------------------------------------- the plugin's own panel */
  var DROP = {SCRIPT: 1, IFRAME: 1, FRAME: 1, FRAMESET: 1, OBJECT: 1, EMBED: 1, APPLET: 1, FORM: 1, META: 1, BASE: 1, LINK: 1, NOSCRIPT: 1, TEMPLATE: 1, PORTAL: 1, SVG: 0};
  function clean(html) {
    var doc = new DOMParser().parseFromString('<!doctype html><body>' + html, 'text/html');
    var all = doc.body.querySelectorAll('*');
    for (var i = all.length - 1; i >= 0; i--) {
      var el = all[i], tag = el.tagName.toUpperCase();
      if (DROP[tag] === 1 || tag.indexOf(':') >= 0) { el.parentNode && el.parentNode.removeChild(el); continue; }
      for (var j = el.attributes.length - 1; j >= 0; j--) {
        var at = el.attributes[j], n = at.name.toLowerCase(), v = String(at.value || '').trim().toLowerCase();
        if (n.indexOf('on') === 0 || n === 'formaction' || n === 'srcdoc' || n === 'ping' || n === 'target') { el.removeAttribute(at.name); continue; }
        if ((n === 'href' || n === 'src' || n === 'xlink:href' || n === 'action' || n === 'poster' || n === 'background') &&
            !(v.indexOf('data:image/') === 0 || v.indexOf('blob:') === 0 || (n === 'href' && v.charAt(0) === '#'))) el.removeAttribute(at.name);
      }
    }
    return doc.body;
  }
  function values() {
    var out = {}, els = box.querySelectorAll('[name]');
    for (var i = 0; i < els.length && i < 200; i++) {
      var el = els[i], n = el.getAttribute('name');
      if (el.type === 'checkbox') out[n] = !!el.checked;
      else if (el.type === 'radio') { if (el.checked) out[n] = el.value; }
      else if ('value' in el) out[n] = String(el.value).slice(0, 20000);
    }
    return out;
  }
  function uiEvent(ev) {
    var t = ev.target, el = t && t.closest ? t.closest('[data-action]') : null;
    if (!el || !box.contains(el)) return;
    if (ev.type === 'click' && (el.tagName === 'SELECT' || (el.tagName === 'INPUT' && el.type !== 'button' && el.type !== 'checkbox' && el.type !== 'radio'))) return;
    if (ev.type === 'click') ev.preventDefault();
    toWorker({t: 'ui', msg: {action: String(el.getAttribute('data-action')).slice(0, 100), value: 'value' in el ? String(el.value).slice(0, 20000) : '', values: values()}});
  }
  box.addEventListener('click', uiEvent);
  box.addEventListener('change', uiEvent);

  function fromHost(d) {
    if (d.t === 'start') start(d);
    else if (d.t === 'res') {
      var p = pending[d.id];
      delete pending[d.id];
      if (p && p.m === 'ui.show' && d.ok) {
        while (box.firstChild) box.removeChild(box.firstChild);
        var body = clean(String((p.a || [])[0] || ''));
        while (body.firstChild) box.appendChild(document.adoptNode(body.firstChild));
      }
      toWorker({t: 'res', id: d.id, ok: !!d.ok, v: d.v, err: d.err});
    } else if (d.t === 'ping') toWorker({t: 'ping', s: d.s});
  }
  window.addEventListener('message', function (e) {
    if (e.source !== host || typeof e.data !== 'string' || e.data.length > 64 * 1024 * 1024) return;
    var d; try { d = JSON.parse(e.data); } catch (err) { return; }
    if (d && typeof d === 'object') fromHost(d);
  });
  toHost({t: 'ready'});
})();

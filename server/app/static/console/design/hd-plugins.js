/* HOOLA DESIGN - D8a PLUGIN RUNTIME, the editor half (docs/HOOLA_DESIGN_PLAN.md section 8, D8a). Styles: design-plugins.css.
   Server half: server/app/design/plugins.py. Runner: plugin-runner.js (the server inlines it into GET /api/design/plugin-frame).

   THE BOX. A plugin's code never runs in this page. Each run gets a fresh <iframe sandbox="allow-scripts"> (never
   allow-same-origin, so its origin is OPAQUE: no localStorage = no token, no cookies, no DOM of this page) loaded from
   /api/design/plugin-frame, a page with its OWN CSP (connect-src 'none', img-src data: blob:, no 'unsafe-eval', the runner
   script allowed by its hash only, frame-ancestors 'self'). The runner starts the code in a Web Worker made from a blob,
   so the code has no DOM at all and a loop that never ends blocks only that worker: the watchdog here removes the iframe,
   which ends the worker, and she is told. The console's own CSP is unchanged (frame-src 'self' already allows the frame,
   and it also stops the frame from navigating itself to another site).

   THE TALK. postMessage, JSON STRINGS only, checked here before anything is parsed: the sender must be THIS run's iframe
   window, at most 1 MB a message, {t:'call', id, m, a:[...]} with m from the method list below and arguments of the right
   shape and size. Every call is checked against the permissions SHE granted for this exact code (the server refuses a run
   whose approval was made for other code: GET /plugins/{id}/run). Edits: every edit call of one command is a
   HD.store.tx with the SAME merge key, so the whole command is ONE undo step (normal multiplayer ops, as they happen);
   node properties only from the section 2 table, every id must exist, at most 10,000 edits a command, refused when the
   file is view only. At most ONE plugin command at a time in an editor.
   Time: while a command runs, the time it spends working (not the time it waits for this page, e.g. a fetch) may not pass
   HD.plugins.config.limitMs (10 s); the worker must answer a ping within limitMs at any time (also while its panel is open);
   a command may last at most totalMs (2 min) in all, and its calls may take at most hostMs (5 s) of this page's own time
   (a flood of finds over a huge page can not freeze the editor). Over any of that = the iframe is removed and a toast says so.

   THE PLUGIN'S API (globals in the worker: `hoola`, and `command` = the menu command chosen; the code is the body of an
   async function, so `await` and `return` work at the top level; every call returns a Promise):
     read     hoola.selection() -> [node]   hoola.select(ids)   hoola.get(id) -> node   hoola.children(id) -> [node]
              hoola.page() -> node          hoola.pages() -> [node]
              hoola.find({type?: 'RECT'|[...], name?, nameContains?, within?: id (default the current page), limit? <= 2000})
     edit     hoola.create(type, parentId, props) -> id   hoola.set(id, props)   hoola.remove(ids)   hoola.move(ids, parentId, beforeId?)
     export   hoola.exportPNG(id, scale=1) -> {type:'image/png', width, height, base64}   hoola.exportSVG(id) -> svg text
     net:host hoola.fetch(url, {method: 'GET'|'POST', body?, base64?, headers?}) -> {status, ok, url, contentType, encoding, body,
              text(), json()}  (made by the SERVER, https + granted hosts only)
     storage  hoola.storage.get(key) / set(key, value) / keys()   (its own, 256 KB)
     always   hoola.notify(text)   hoola.close()   hoola.command   hoola.manifest
     ui:true  hoola.ui.show(html, {title?, width?, height?})  draws html in its own panel (cleaned: no scripts, no frames, no forms,
              no outside links); hoola.ui.on(fn)  fn({action, value, values}) for a click / change on an element with
              data-action (values = every named field);  hoola.ui.close()
     A node = {id, type, parent, idx, name, ...the props it carries} (section 2; a missing prop = its default).
     The command ends when the code returns - unless it showed its panel: then it stays until hoola.close() or she closes it.

   FOR OTHER CODE (D8b "Ask Hoola to make a plugin" hands its result here; nothing is installed without her OK):
     HD.plugins.install(manifest, code)  -> Promise<{installed, id, granted: [...]}>  opens the REVIEW dialog first (the code,
                                            every permission in plain words, ticked); only her Install installs + approves
     HD.plugins.run(id, command?)        -> Promise<{ok, error?, edits}>   (command defaults to the first menu command)
     HD.plugins.list(force?)             -> Promise<[plugin summary]>      HD.plugins.validate(manifest, code) -> [problems]
     HD.plugins.open()  (manage)   HD.plugins.write(prefill?)  (the code editor)   HD.plugins.stop()   HD.plugins.active
     HD.plugins.config {limitMs, totalMs, ...}   HD.plugins.METHODS (the API names)   HD.plugins.words(permission) (plain words)
   Every text from a plugin is set with textContent here; its panel html is drawn only INSIDE its sandbox. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const ui = HD.ui;
  if (!ui || !ui.h) return;
  const h = ui.h, enc = encodeURIComponent;
  const S = () => HD.store;
  const ROOT = '0:0';
  const config = {limitMs: 10000, totalMs: 120000, pingMs: 1000, readyMs: 15000, uiMaxMs: 30 * 60 * 1000,
    msgMax: 1024 * 1024, hostMs: 5000, editMax: 10000, findMax: 2000, outMax: 24 * 1024 * 1024, htmlMax: 512 * 1024, propsMax: 256 * 1024};
  const FRAME_URL = '/api/design/plugin-frame';
  const CODE_MAX = 200 * 1024;
  const ID_RE = /^[a-z0-9][a-z0-9._-]{1,63}$/, CMD_RE = /^[A-Za-z0-9_.-]{1,40}$/;
  const HOST_RE = /^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$/;
  const BASE = ['read', 'edit', 'export', 'storage'];
  const st = {list: null, loading: null};
  let active = null, runSeq = 0;

  /* ---------------------------------------------------------------- permissions in plain words */
  function words(p) {
    if (p === 'read') return 'Read your design: layers, their text and what you have selected';
    if (p === 'edit') return 'Change your design: add, change, move and delete layers';
    if (p === 'export') return 'Make pictures of layers (PNG and SVG)';
    if (p === 'storage') return 'Keep a little data of its own (up to 256 KB)';
    if (/^net:/.test(p)) return 'Send data to ' + p.slice(4) + ' and get answers from it';
    return p;
  }
  function permOk(p) {
    if (BASE.indexOf(p) >= 0) return true;
    if (typeof p !== 'string' || p.indexOf('net:') !== 0) return false;
    const host = p.slice(4);
    return HOST_RE.test(host) && !/^[\d.]+$/.test(host) && host.indexOf(':') < 0;
  }

  /* ---------------------------------------------------------------- validation (the server checks it all again) */
  function validate(m, code) {
    const out = [];
    if (!m || typeof m !== 'object' || Array.isArray(m)) return ['The manifest must be an object.'];
    if (typeof m.id !== 'string' || !ID_RE.test(m.id)) out.push("The id must be 2-64 characters: small letters, digits, '.', '_' or '-'.");
    if (typeof m.name !== 'string' || !m.name.trim()) out.push('The plugin needs a name.');
    else if (m.name.length > 80) out.push('The name is longer than 80 characters.');
    if (m.description !== undefined && (typeof m.description !== 'string' || m.description.length > 500)) out.push('The description must be text of at most 500 characters.');
    if (m.version !== undefined && (typeof m.version !== 'string' || m.version.length > 20)) out.push('The version must be short text.');
    if (m.permissions !== undefined && !Array.isArray(m.permissions)) out.push('permissions must be a list.');
    for (const p of m.permissions || []) if (!permOk(typeof p === 'string' && p.indexOf('net:') === 0 ? 'net:' + p.slice(4).trim().toLowerCase() : p)) out.push("'" + String(p).slice(0, 60) + "' is not a permission.");
    if (m.ui !== undefined && typeof m.ui !== 'boolean') out.push('ui must be true or false.');
    if (m.menu !== undefined) {
      if (!Array.isArray(m.menu) || m.menu.length > 20) out.push('menu must be a list of at most 20 commands.');
      else { const seen = new Set();
        for (const it of m.menu) { if (!it || typeof it.label !== 'string' || !it.label.trim() || it.label.length > 60) out.push('Every menu entry needs a label (at most 60 characters).');
          if (!it || typeof it.command !== 'string' || !CMD_RE.test(it.command)) out.push('A menu command is 1-40 letters, digits, ".", "_" or "-".');
          else if (seen.has(it.command)) out.push("The command '" + it.command + "' is in the menu twice."); else seen.add(it.command); } }
    }
    if (typeof code !== 'string' || !code.trim()) out.push('The plugin has no code.');
    else if (new Blob([code]).size > CODE_MAX) out.push('The code is larger than 200 KB.');
    return out;
  }

  /* ---------------------------------------------------------------- the server */
  async function list(force) {
    if (!signedIn()) return [];
    if (st.list && !force) return st.list;
    if (!st.loading) st.loading = ui.api('GET', '/plugins').then(d => { st.list = (d && d.plugins) || []; commands(); return st.list; }).finally(() => { st.loading = null; });
    return st.loading;
  }
  function signedIn() { return !!ui.token && !(HD.net && HD.net.share); }
  function known(id) { return (st.list || []).find(p => p.id === id) || null; }
  function ready(p) { return !!(p && p.enabled && p.approved); }

  /* ---------------------------------------------------------------- reading the document */
  function has(id) { return typeof id === 'string' && id.length <= 64 && S().has(id); }
  function needId(id, what) { if (!has(id)) throw new Error((what || 'The layer') + ' ' + JSON.stringify(String(id).slice(0, 64)) + ' does not exist.'); return id; }
  function idList(ids, max) {
    if (typeof ids === 'string') ids = [ids];
    if (!Array.isArray(ids)) throw new Error('Give a list of layer ids.');
    if (ids.length > max) throw new Error('At most ' + max + ' layers at a time.');
    const out = [];
    for (const id of ids) { needId(id); if (out.indexOf(id) < 0) out.push(id); }
    return out;
  }
  function node(id) { const n = S().get(id); if (!n) return null; const o = JSON.parse(JSON.stringify(n)); o.id = id; return o; }
  function find(q) {
    if (!q || typeof q !== 'object' || Array.isArray(q)) throw new Error('find takes an object: {type, name, nameContains, within, limit}.');
    const within = q.within === undefined || q.within === null ? HD.sel.page : needId(q.within);
    const types = q.type === undefined || q.type === null ? null : [].concat(q.type).map(String);
    const name = typeof q.name === 'string' ? q.name : null, part = typeof q.nameContains === 'string' ? q.nameContains.toLowerCase() : null;
    const limit = Math.max(1, Math.min(config.findMax, +q.limit || config.findMax)), out = [];
    S().walk(within, (id, n) => {
      if (out.length >= limit) return false;
      if (id === within) return true;
      if ((!types || types.indexOf(n.type) >= 0) && (name === null || n.name === name) && (part === null || String(n.name || '').toLowerCase().indexOf(part) >= 0)) out.push(node(id));
      return true;
    });
    return out;
  }

  /* ---------------------------------------------------------------- node properties: section 2, nothing else */
  const P = {};
  ['x', 'y', 'w', 'h', 'rot', 'opacity', 'strokeWeight', 'sides', 'ratio', 'fontSize', 'fontWeight', 'letterSpacing', 'minW', 'maxW', 'minH', 'maxH'].forEach(k => { P[k] = 'num'; });
  ['flipH', 'flipV', 'visible', 'locked', 'mask', 'clip', 'italic', 'protoStart', 'fixed'].forEach(k => { P[k] = 'bool'; });
  ['fills', 'strokes', 'dash', 'effects', 'grids', 'runs', 'reactions', 'exports', 'guides', 'modes'].forEach(k => { P[k] = 'arr'; });
  ['layout', 'cons', 'ov', 'bind', 'styles', 'vars'].forEach(k => { P[k] = 'obj'; });
  Object.assign(P, {name: ['str', 200], chars: ['str', 100000], font: ['str', 120], path: ['str', 262144], desc: ['str', 4000], comp: ['str', 64],
    fillStyle: ['str', 64], textStyle: ['str', 64], effectStyle: ['str', 64], blend: ['str', 40], radius: 'radius', lineHeight: 'lh', bg: 'hex',
    strokeAlign: ['center', 'inside', 'outside'], strokeCap: ['butt', 'round', 'square'], strokeJoin: ['miter', 'round', 'bevel'],
    sizeH: ['fixed', 'hug', 'fill'], sizeV: ['fixed', 'hug', 'fill'], layoutPos: ['auto', 'absolute'], fillRule: ['nonzero', 'evenodd'],
    align: ['left', 'center', 'right', 'justify'], alignV: ['top', 'middle', 'bottom'], autoResize: ['wh', 'h', 'none'],
    decoration: ['none', 'underline', 'strike'], textCase: ['none', 'upper', 'lower', 'title'], scroll: ['none', 'v', 'h', 'both'],
    bool: ['union', 'subtract', 'intersect', 'exclude']});
  const fin = v => typeof v === 'number' && isFinite(v);
  function depthOk(v, d) { if (d > 12) return false; if (v === null || typeof v !== 'object') return typeof v !== 'function' && (typeof v !== 'number' || isFinite(v));
    if (Array.isArray(v)) return v.every(x => depthOk(x, d + 1)); if (Object.getPrototypeOf(v) !== Object.prototype) return false; return Object.keys(v).every(k => depthOk(v[k], d + 1)); }
  function plain(v) { return v !== null && typeof v === 'object' && !Array.isArray(v) && Object.getPrototypeOf(v) === Object.prototype; }
  function cleanProps(p, allowNull) {
    if (p === undefined || p === null) return {};
    if (!plain(p)) throw new Error('Layer properties must be a plain object.');
    const keys = Object.keys(p);
    if (keys.length > 120) throw new Error('Too many properties at once.');
    if (JSON.stringify(p).length > config.propsMax) throw new Error('Those properties are larger than 256 KB.');
    const out = {};
    for (const k of keys) {
      const v = p[k], kind = P[k];
      if (kind === undefined) throw new Error("'" + k.slice(0, 40) + "' is not a layer property" + ({parent: 1, idx: 1, type: 1}[k] ? ' that can be set (use hoola.move to move a layer).' : '.'));
      if (v === null) { if (allowNull) out[k] = null; continue; }
      if (v === undefined) continue;
      let good;
      if (kind === 'num') good = fin(v);
      else if (kind === 'bool') good = typeof v === 'boolean';
      else if (kind === 'arr') good = Array.isArray(v) && v.length <= 2000 && depthOk(v, 0);
      else if (kind === 'obj') good = plain(v) && depthOk(v, 0);
      else if (kind === 'radius') good = fin(v) || (Array.isArray(v) && v.length === 4 && v.every(fin));
      else if (kind === 'lh') good = fin(v) || v === 'auto';
      else if (kind === 'hex') good = typeof v === 'string' && /^#[0-9A-Fa-f]{6}$/.test(v);
      else if (kind[0] === 'str') good = typeof v === 'string' && v.length <= kind[1];
      else good = kind.indexOf(v) >= 0;
      if (!good) throw new Error("The value of '" + k + "' is not right for a layer (see the property table).");
      out[k] = JSON.parse(JSON.stringify(v));
    }
    return out;
  }

  /* ---------------------------------------------------------------- the calls */
  function edit(slot, n, fn) {
    if (S().readOnly || !(HD.tools && HD.tools.u && HD.tools.u.canEdit())) throw new Error('This file is view only: the plugin can not change it.');
    if (slot.edits + n > config.editMax) throw new Error('A plugin command may make at most ' + config.editMax + ' changes.');
    let res;
    S().tx('Plugin: ' + slot.name, () => { res = fn(); }, {merge: 'hdplugin:' + slot.runId});
    slot.edits += n;
    return res;
  }
  const METHODS = {
    selection: {perm: 'read', fn: () => (HD.sel.ids || []).filter(has).slice(0, config.findMax).map(node)},
    select: {perm: 'read', fn: (s, ids) => { const l = idList(ids, config.findMax); HD.sel.set(l); return l; }},
    get: {perm: 'read', fn: (s, id) => node(needId(id))},
    children: {perm: 'read', fn: (s, id) => S().children(needId(id)).slice(0, config.findMax).map(node)},
    page: {perm: 'read', fn: () => node(HD.sel.page)},
    pages: {perm: 'read', fn: () => S().pages().map(node)},
    find: {perm: 'read', fn: (s, q) => find(q)},
    create: {perm: 'edit', fn: (s, type, parent, props) => {
      if (typeof type !== 'string' || S().TYPES.indexOf(type) < 0 || type === 'DOCUMENT') throw new Error('Unknown layer type ' + JSON.stringify(String(type).slice(0, 40)) + '.');
      needId(parent, 'The parent');
      if ((type === 'PAGE') !== (parent === ROOT)) throw new Error(type === 'PAGE' ? 'A page goes in the document (parent "0:0").' : 'A layer goes on a page or inside a layer, not in the document itself.');
      const pp = cleanProps(props, false);
      return edit(s, 1, () => S().create(type, parent, pp));
    }},
    set: {perm: 'edit', fn: (s, id, props) => {
      needId(id);
      const pp = cleanProps(props, true);
      if (id === ROOT && Object.keys(pp).some(k => ['styles', 'vars', 'modes', 'name'].indexOf(k) < 0)) throw new Error('Only styles, variables and modes can be set on the document.');
      return !!edit(s, 1, () => S().set(id, pp));
    }},
    remove: {perm: 'edit', fn: (s, ids) => {
      const l = idList(ids, config.editMax);
      if (l.indexOf(ROOT) >= 0) throw new Error('The document itself can not be removed.');
      const pages = S().pages();
      if (pages.length && pages.every(pg => l.indexOf(pg) >= 0)) throw new Error('The last page can not be removed.');
      return !!edit(s, l.length, () => S().remove(l));
    }},
    move: {perm: 'edit', fn: (s, ids, parent, before) => {
      const l = idList(ids, config.editMax);
      if (l.indexOf(ROOT) >= 0) throw new Error('The document itself can not be moved.');
      needId(parent, 'The parent');
      if (before !== null && before !== undefined) needId(before, 'The layer to go before');
      if (l.some(id => (S().get(id).type === 'PAGE') !== (parent === ROOT))) throw new Error('Pages stay in the document and layers stay on pages.');
      return !!edit(s, l.length, () => S().move(l, parent, before === undefined ? null : before));
    }},
    notify: {perm: null, fn: (s, text) => { ui.toast(s.name + ': ' + String(text).slice(0, 240)); return true; }},
    exportPNG: {perm: 'export', slow: true, fn: async (s, id, scale) => {
      needId(id);
      scale = fin(scale) ? Math.max(0.05, Math.min(4, scale)) : 1;
      try { await HD.render.ready(id, 5000); } catch (e) { /* drawn with what has arrived */ }
      const cv = HD.render.toCanvas(id, scale, {});
      if (!cv || cv.width * cv.height > 25e6) throw new Error('That picture would be too large.');
      const b64 = String(cv.toDataURL('image/png')).split(',')[1] || '';
      if (b64.length > config.outMax) throw new Error('That picture would be too large.');
      return {type: 'image/png', width: cv.width, height: cv.height, base64: b64};
    }},
    exportSVG: {perm: 'export', slow: true, fn: async (s, id) => {
      needId(id);
      try { await HD.render.ready(id, 5000); } catch (e) { /* as it is */ }
      const svg = String(HD.render.toSVG(id, {}) || '');
      if (svg.length > config.outMax) throw new Error('That SVG would be too large.');
      return svg;
    }},
    fetch: {perm: 'net', slow: true, fn: async (s, url, opts) => {
      if (typeof url !== 'string' || url.length > 4096) throw new Error('Give the address to fetch.');
      let host = '';
      try { const u = new URL(url); if (u.protocol !== 'https:') throw new Error('x'); host = u.hostname.toLowerCase(); } catch (e) { throw new Error('A plugin may only fetch https:// addresses.'); }
      if (!s.perms.has('net:' + host)) throw new Error('This plugin may not talk to ' + host + ': you did not give it that host.');
      opts = plain(opts) ? opts : {};
      const body = {url: url, method: String(opts.method || 'GET').toUpperCase()};
      if (opts.body !== undefined && opts.body !== null) { if (typeof opts.body !== 'string') throw new Error('The body must be text.'); body.body = opts.body; }
      if (opts.base64) body.base64 = true;
      if (plain(opts.headers)) body.headers = opts.headers;
      return ui.api('POST', '/plugins/' + enc(s.pid) + '/fetch', body);
    }},
    'storage.get': {perm: 'storage', slow: true, fn: async (s, key) => { const d = await store(s); key = skey(key); return Object.prototype.hasOwnProperty.call(d, key) ? d[key] : null; }},
    'storage.keys': {perm: 'storage', slow: true, fn: async (s) => Object.keys(await store(s))},
    'storage.set': {perm: 'storage', slow: true, fn: async (s, key, value) => {
      key = skey(key);
      if (!depthOk(value, 0)) throw new Error('Only plain data can be kept.');
      const d = Object.assign({}, await store(s));
      if (value === null) delete d[key]; else d[key] = value;
      const got = await ui.api('PUT', '/plugins/' + enc(s.pid) + '/storage', {data: d});
      s.store = (got && got.data) || d;
      return true;
    }},
    'ui.show': {perm: 'ui', fn: (s, html, opts) => {
      if (typeof html !== 'string' || html.length > config.htmlMax) throw new Error('The panel is larger than 512 KB.');
      showPanel(s, plain(opts) ? opts : {});
      return true;
    }},
    close: {perm: null, fn: (s) => { setTimeout(() => finish(s, true, ''), 0); return true; }}
  };
  function skey(k) { if (typeof k !== 'string' || !k || k.length > 200) throw new Error('A storage key is text of at most 200 characters.'); return k; }
  async function store(s) { if (!s.store) { const got = await ui.api('GET', '/plugins/' + enc(s.pid) + '/storage'); s.store = (got && got.data) || {}; } return s.store; }
  function allowed(s, perm) {
    if (perm === null) return true;
    if (perm === 'ui') return !!s.manifest.ui;
    if (perm === 'net') return Array.from(s.perms).some(p => p.indexOf('net:') === 0);
    return s.perms.has(perm);
  }
  const REFUSED = {read: 'reading your design', edit: 'changing your design', export: 'making pictures', storage: 'keeping data', net: 'talking to the internet', ui: 'showing a panel (its manifest says ui: false)'};

  async function call(s, d) {
    const id = d.id;
    const reply = (ok, v, err) => { if (active === s) post(s, ok ? {t: 'res', id: id, ok: true, v: v === undefined ? null : v} : {t: 'res', id: id, ok: false, err: String(err)}); };
    const m = Object.prototype.hasOwnProperty.call(METHODS, d.m) ? METHODS[d.m] : null;
    if (!m) return reply(false, null, 'hoola has no ' + JSON.stringify(String(d.m).slice(0, 40)) + '.');
    if (!Array.isArray(d.a) || d.a.length > 4) return reply(false, null, 'Wrong arguments.');
    if (!allowed(s, m.perm)) { s.refused++; return reply(false, null, 'You did not give this plugin permission for ' + (REFUSED[m.perm] || m.perm) + '.'); }
    s.calls++;
    if (m.slow) s.inflight++;
    const t0 = performance.now();
    try { const run = m.fn.apply(null, [s].concat(d.a)); if (!m.slow) s.hostMs += performance.now() - t0;
      if (s.hostMs > config.hostMs) { setTimeout(() => finish(s, false, s.name + ' asked too much of the editor at once, so it was stopped.'), 0); return reply(false, null, 'Stopped.'); }
      reply(true, await run); }
    catch (e) { reply(false, null, (e && e.message) || 'Refused.'); }
    finally { if (m.slow) s.inflight--; }
  }

  /* ---------------------------------------------------------------- the run */
  function post(s, obj) { try { s.frame.contentWindow.postMessage(JSON.stringify(obj), '*'); } catch (e) { /* the frame is gone */ } }
  window.addEventListener('message', ev => {
    const s = active;
    if (!s || !s.frame || ev.source !== s.frame.contentWindow) return;
    if (typeof ev.data !== 'string') return;
    if (ev.data.length > config.msgMax) { finish(s, false, s.name + ' sent a message larger than 1 MB, so it was stopped.'); return; }
    let d; try { d = JSON.parse(ev.data); } catch (e) { return; }
    if (!d || typeof d !== 'object' || Array.isArray(d)) return;
    if (d.t === 'ready') { if (s.state !== 'loading') return; s.state = 'running'; s.lastPong = performance.now(); s.mark = performance.now();
      post(s, {t: 'start', code: s.code, command: s.command, manifest: {id: s.pid, name: s.name, version: s.manifest.version, permissions: Array.from(s.perms), ui: !!s.manifest.ui}}); }
    else if (d.t === 'pong') s.lastPong = performance.now();
    else if (d.t === 'call') { if (s.state !== 'running' && s.state !== 'idle') return; if (!(typeof d.id === 'number' && d.id > 0 && d.id < 1e12)) return; call(s, d); }
    else if (d.t === 'end') { if (s.ui) { s.state = 'idle'; } else finish(s, true, ''); }
    else if (d.t === 'fail') finish(s, false, s.name + ' stopped with an error' + (d.line ? ' on line ' + (+d.line) : '') + ': ' + String(d.error || '').slice(0, 300));
  });
  function tick(s) {
    if (active !== s) return;
    const t = performance.now(), dt = t - s.mark; s.mark = t;
    if (s.state === 'loading') { if (t - s.started > config.readyMs) finish(s, false, s.name + ' could not start.'); return; }
    if (s.state === 'running' && !s.inflight) s.spent += dt;
    if (s.state === 'running' && s.spent > config.limitMs) { finish(s, false, s.name + ' took longer than ' + Math.round(config.limitMs / 1000) + ' seconds, so it was stopped.'); return; }
    if (t - s.lastPong > config.limitMs + config.pingMs) { finish(s, false, s.name + ' stopped answering, so it was stopped.'); return; }
    if (s.state === 'running' && t - s.started > config.totalMs) { finish(s, false, s.name + ' ran for too long, so it was stopped.'); return; }
    if (s.state === 'idle' && t - s.started > config.uiMaxMs) { finish(s, true, ''); return; }
    if (t - s.pinged >= config.pingMs) { s.pinged = t; post(s, {t: 'ping', s: Math.round(t)}); }
  }
  function finish(s, ok, msg) {
    if (active !== s) return;
    active = null;
    clearInterval(s.timer);
    if (s.frame && s.frame.parentNode) s.frame.parentNode.removeChild(s.frame);      /* ends the worker too */
    s.frame = null;
    if (s.holder && s.holder.parentNode) s.holder.parentNode.removeChild(s.holder);
    if (!ok && msg) ui.toast(msg, true);
    paintActive();
    if (s.resolve) s.resolve({ok: !!ok, error: ok ? undefined : (msg || 'Stopped.'), edits: s.edits, calls: s.calls, refused: s.refused});
  }
  function stop() { if (active) finish(active, false, active.name + ' was stopped.'); }

  async function run(pid, command) {
    if (!signedIn()) { ui.toast('Sign in to use plugins.'); return {ok: false, error: 'Sign in to use plugins.'}; }
    if (!HD.app || !HD.app.file) { ui.toast('Open a file first.'); return {ok: false, error: 'Open a file first.'}; }
    if (active) { ui.toast('A plugin is already running. Let it finish or stop it first.', true); return {ok: false, error: 'busy'}; }
    const s = active = {runId: ++runSeq, pid: String(pid), command: '', state: 'fetching', name: String(pid), edits: 0, calls: 0, refused: 0, inflight: 0, spent: 0, hostMs: 0, ui: false};
    let got;
    try { got = await ui.api('GET', '/plugins/' + enc(pid) + '/run'); }
    catch (e) { active = null; const msg = (e && e.message) || 'The plugin can not run.'; ui.toast(msg, true); return {ok: false, error: msg}; }
    if (active !== s) return {ok: false, error: 'Stopped.'};
    const man = (got.plugin && got.plugin.manifest) || {}, menu = Array.isArray(man.menu) ? man.menu : [];
    s.manifest = man; s.name = String(man.name || pid).slice(0, 80); s.code = String(got.code || '');
    s.perms = new Set((got.permissions || []).filter(p => typeof p === 'string'));
    s.command = command === undefined || command === null ? (menu[0] ? menu[0].command : 'run') : String(command);
    if (menu.length && !menu.some(it => it.command === s.command)) { active = null; const msg = s.name + ' has no command ' + JSON.stringify(s.command) + '.'; ui.toast(msg, true); return {ok: false, error: msg}; }
    return new Promise(resolve => {
      s.resolve = resolve;
      const fr = document.createElement('iframe');
      fr.setAttribute('sandbox', 'allow-scripts');                  /* NEVER allow-same-origin: the frame's origin stays opaque */
      fr.setAttribute('referrerpolicy', 'no-referrer');
      fr.setAttribute('allow', "camera 'none'; microphone 'none'; geolocation 'none'; clipboard-read 'none'; clipboard-write 'none'; payment 'none'; usb 'none'; serial 'none'; hid 'none'; bluetooth 'none'; display-capture 'none'");
      fr.setAttribute('title', 'Plugin: ' + s.name);
      fr.className = 'hdp-frame';
      s.frame = fr;
      if (man.ui) { s.holder = panelFor(s); } else { s.holder = h('div', {class: 'hdp-hidden', 'aria-hidden': 'true'}); s.holder.appendChild(fr); document.body.appendChild(s.holder); }
      s.state = 'loading'; s.started = s.mark = s.lastPong = s.pinged = performance.now();
      s.timer = setInterval(() => tick(s), 100);
      fr.src = FRAME_URL;
      paintActive();
    });
  }

  /* ---------------------------------------------------------------- a plugin's own panel (its sandboxed iframe) */
  function panelFor(s) {
    const close = h('button', {type: 'button', class: 'hd-ib', title: 'Close the plugin', 'aria-label': 'Close the plugin', on: {click: () => finish(s, true, '')}}, ui.icon('close'));
    const title = h('strong', {class: 'hdp-ptitle', text: s.name});
    const head = h('div', {class: 'hdp-phead'}, ui.icon('spark'), title, close);
    const body = h('div', {class: 'hdp-pbody'}, s.frame);
    const el = h('section', {class: 'hdp-panel', role: 'dialog', 'aria-label': 'Plugin: ' + s.name, hidden: true}, head, body);
    s.ptitle = title;
    drag(head, el);
    document.body.appendChild(el);
    return el;
  }
  function showPanel(s, opts) {
    if (!s.holder || !s.manifest.ui) return;
    s.ui = true;
    const w = fin(opts.width) ? Math.max(240, Math.min(640, opts.width)) : 320, hh = fin(opts.height) ? Math.max(160, Math.min(800, opts.height)) : 420;
    s.holder.style.width = w + 'px'; s.holder.querySelector('.hdp-pbody').style.height = hh + 'px';
    if (typeof opts.title === 'string' && opts.title.trim()) s.ptitle.textContent = s.name + ' · ' + opts.title.trim().slice(0, 60);
    s.holder.hidden = false;
  }
  function drag(handle, el) {
    handle.addEventListener('pointerdown', ev => {
      if (ev.target.closest('button')) return;
      const r = el.getBoundingClientRect(), ox = ev.clientX - r.left, oy = ev.clientY - r.top;
      handle.setPointerCapture(ev.pointerId);
      const mv = e => { el.style.left = Math.max(0, Math.min(innerWidth - 80, e.clientX - ox)) + 'px'; el.style.top = Math.max(0, Math.min(innerHeight - 40, e.clientY - oy)) + 'px'; el.style.right = 'auto'; };
      const up = () => { handle.removeEventListener('pointermove', mv); handle.removeEventListener('pointerup', up); };
      handle.addEventListener('pointermove', mv); handle.addEventListener('pointerup', up);
    });
  }
  /* the small "a plugin is running" chip with Stop */
  let chip = null;
  function paintActive() {
    const s = active;
    if (!s || s.ui) { if (chip) { chip.remove(); chip = null; } return; }
    if (!chip) { chip = h('div', {class: 'hdp-running', role: 'status'}); document.body.appendChild(chip); }
    ui.clear(chip);
    chip.appendChild(h('span', {class: 'hdp-dot', 'aria-hidden': 'true'}));
    chip.appendChild(h('span', {text: s.name + ' is running…'}));
    chip.appendChild(h('button', {type: 'button', class: 'hd-btn', text: 'Stop', on: {click: stop}}));
  }

  /* ---------------------------------------------------------------- dialogs */
  function head(title) {
    return h('div', {class: 'hd-sheethead'}, h('h2', {text: title}), h('button', {type: 'button', class: 'hd-ib', title: 'Close', 'aria-label': 'Close', on: {click: () => ui.closeModal()}}, ui.icon('close')));
  }
  function codeView(code) {
    const lines = String(code).split('\n'), gut = h('pre', {class: 'hdp-gut', 'aria-hidden': 'true', text: lines.map((_, i) => i + 1).join('\n')});
    return h('div', {class: 'hdp-code ro'}, gut, h('pre', {class: 'hdp-src', tabIndex: 0, 'aria-label': 'The plugin code', text: code}));
  }

  /* review: the code + every permission in plain words BEFORE anything is installed or approved */
  function review(manifest, code, o) {
    o = o || {};
    return new Promise(resolve => {
      const probs = validate(manifest, code);
      let done = false;
      const end = v => { if (!done) { done = true; resolve(v); } };
      const m = manifest || {};
      const perms = (Array.isArray(m.permissions) ? m.permissions : []).map(p => typeof p === 'string' && p.indexOf('net:') === 0 ? 'net:' + p.slice(4).trim().toLowerCase() : p);
      const boxes = [];
      const plist = h('ul', {class: 'hdp-perms'});
      for (const p of perms) { const cb = h('input', {type: 'checkbox', checked: true, 'aria-label': words(String(p))}); cb.dataset.perm = String(p); boxes.push(cb);
        plist.appendChild(h('li', {class: /^net:/.test(p) || p === 'edit' ? 'hdp-strong' : ''}, h('label', null, cb, h('span', {text: words(String(p))})))); }
      if (!perms.length) plist.appendChild(h('li', {class: 'hdp-none', text: 'It asks for nothing: it can only show a message.'}));
      const status = h('p', {class: 'hdp-status', role: 'status', 'aria-live': 'polite', text: probs.join(' ')});
      const go = h('button', {type: 'button', class: 'hd-btn pri', text: o.mode === 'approve' ? 'Approve' : 'Install', disabled: !!probs.length});
      const cancel = h('button', {type: 'button', class: 'hd-btn', text: 'Cancel', on: {click: () => { ui.closeModal(); end({installed: false, id: m.id, granted: []}); }}});
      go.addEventListener('click', async () => {
        go.disabled = true; status.textContent = o.mode === 'approve' ? 'Approving…' : 'Installing…';
        const granted = boxes.filter(b => b.checked).map(b => b.dataset.perm);
        try {
          let sha = o.codeSha;
          if (o.mode !== 'approve') { const got = await ui.api('POST', '/plugins', {manifest: m, code: code}); sha = got.plugin.code_sha; }
          await ui.api('POST', '/plugins/' + enc(m.id) + '/grant', {permissions: granted, code_sha: sha});
          await list(true);
          ui.closeModal(); ui.toast((m.name || m.id) + (o.mode === 'approve' ? ' is approved.' : ' is installed.'));
          end({installed: true, id: m.id, granted: granted});
        } catch (e) { status.textContent = (e && e.message) || 'That did not work.'; go.disabled = false; }
      });
      ui.modal('hdp-dialog hdp-review', 'Review a plugin', [
        head(o.mode === 'approve' ? 'Approve this plugin?' : 'Install this plugin?'),
        h('div', {class: 'hdp-body'},
          h('div', {class: 'hdp-who'}, h('strong', {text: String(m.name || m.id || 'Plugin')}), h('span', {class: 'hdp-ver', text: (m.version ? 'version ' + m.version + ' · ' : '') + String(m.id || '')})),
          m.description ? h('p', {class: 'hdp-desc', text: String(m.description)}) : null,
          o.note ? h('p', {class: 'hdp-warn', text: o.note}) : null,
          h('h3', {class: 'hdp-h3', text: 'It asks to'}), plist,
          m.ui ? h('p', {class: 'hdp-note', text: 'It shows its own panel while it runs.'}) : null,
          h('p', {class: 'hdp-note', text: 'A plugin runs in a sealed box: it can not see your sign-in, your other files or this page. It can do only what is ticked here, and only through Hoola. If its code changes, you are asked again.'}),
          h('h3', {class: 'hdp-h3', text: 'Its code'}), codeView(String(code || ''))),
        h('div', {class: 'hdp-foot'}, status, cancel, go)]);
      go.focus({preventScroll: true});
      const mo = new MutationObserver(() => { if (!document.contains(go)) { mo.disconnect(); end({installed: false, id: m.id, granted: []}); } });
      mo.observe(document.body, {childList: true, subtree: true});
    });
  }
  function install(manifest, code) { return review(manifest, code, {mode: 'install'}); }

  async function approve(pid) {
    let got;
    try { got = (await ui.api('GET', '/plugins/' + enc(pid))).plugin; } catch (e) { ui.toast((e && e.message) || 'The plugin could not be read.', true); return {installed: false}; }
    return review(got.manifest, got.code, {mode: 'approve', codeSha: got.code_sha, note: got.stale_grant ? 'Its code changed after you approved it. Look at it again.' : ''});
  }

  async function openManager() {
    if (!signedIn()) { ui.toast('Sign in to use plugins.'); return; }
    const body = h('div', {class: 'hdp-body hdp-list', 'aria-live': 'polite'}, h('p', {class: 'hdp-note', text: 'Loading your plugins…'}));
    ui.modal('hdp-dialog hdp-manager', 'Plugins', [head('Plugins'), body,
      h('div', {class: 'hdp-foot'}, h('p', {class: 'hdp-status', text: 'Plugins run in a sealed box and can only do what you allow.'}),
        h('button', {type: 'button', class: 'hd-btn pri', text: 'Write a plugin', on: {click: () => write()}}))]);
    let items;
    try { items = await list(true); } catch (e) { ui.clear(body).appendChild(h('p', {class: 'hdp-warn', text: (e && e.message) || 'Your plugins could not be listed.'})); return; }
    paintList(body, items);
  }
  function paintList(body, items) {
    ui.clear(body);
    if (!items.length) { body.appendChild(h('p', {class: 'hdp-none', text: 'No plugins yet. Write one, or ask Hoola to make one.'})); return; }
    for (const p of items) {
      const m = p.manifest || {}, state = !p.enabled ? ['off', 'Switched off'] : p.stale_grant ? ['warn', 'Code changed: look again'] : !p.approved ? ['warn', 'Waiting for your approval'] : ['ok', 'Ready'];
      const acts = h('div', {class: 'hdp-acts'});
      for (const it of (m.menu || []).slice(0, 6)) acts.appendChild(h('button', {type: 'button', class: 'hd-btn pri', text: (m.menu.length > 1 ? it.label : 'Run'), disabled: !ready(p),
        on: {click: () => { ui.closeModal(); run(p.id, it.command); }}}));
      if (!p.approved) acts.appendChild(h('button', {type: 'button', class: 'hd-btn', text: 'Review and approve', on: {click: () => approve(p.id)}}));
      const more = h('div', {class: 'hdp-more', hidden: true},
        h('h3', {class: 'hdp-h3', text: 'Permissions'}),
        h('ul', {class: 'hdp-perms'}, (m.permissions || []).length ? (m.permissions || []).map(x => h('li', null, h('span', {class: 'hdp-tick ' + ((p.granted || []).indexOf(x) >= 0 ? 'yes' : 'no'), text: (p.granted || []).indexOf(x) >= 0 ? 'Allowed' : 'Not allowed'}), h('span', {text: words(x)})))
          : h('li', {class: 'hdp-none', text: 'It asks for nothing.'})),
        h('div', {class: 'hdp-acts'},
          h('button', {type: 'button', class: 'hd-btn', text: p.enabled ? 'Switch off' : 'Switch on', on: {click: async () => { try { await ui.api('PATCH', '/plugins/' + enc(p.id), {enabled: !p.enabled}); paintList(body, await list(true)); } catch (e) { ui.toast(e.message, true); } }}}),
          h('button', {type: 'button', class: 'hd-btn', text: 'Look again and approve', on: {click: () => approve(p.id)}}),
          h('button', {type: 'button', class: 'hd-btn', text: 'Edit code', on: {click: async () => { try { const got = (await ui.api('GET', '/plugins/' + enc(p.id))).plugin; write({manifest: got.manifest, code: got.code}); } catch (e) { ui.toast(e.message, true); } }}}),
          rmButton(p, body)));
      const toggle = h('button', {type: 'button', class: 'hd-btn', text: 'Manage', 'aria-expanded': 'false', on: {click: () => { more.hidden = !more.hidden; toggle.setAttribute('aria-expanded', String(!more.hidden)); }}});
      acts.appendChild(toggle);
      body.appendChild(h('article', {class: 'hdp-item', 'data-plugin': p.id},
        h('div', {class: 'hdp-row'}, h('div', {class: 'hdp-who'}, h('strong', {text: String(m.name || p.id)}), h('span', {class: 'hdp-ver', text: (m.version ? 'v' + m.version + ' · ' : '') + p.id})),
          h('span', {class: 'hdp-state ' + state[0], text: state[1]})),
        m.description ? h('p', {class: 'hdp-desc', text: String(m.description)}) : null,
        h('div', {class: 'hdp-chips'}, (m.permissions || []).map(x => h('span', {class: 'hdp-chip', title: words(x), text: /^net:/.test(x) ? x.slice(4) : x}))),
        acts, more));
    }
  }
  function rmButton(p, body) {
    const b = h('button', {type: 'button', class: 'hd-btn hdp-danger', text: 'Remove'});
    b.addEventListener('click', async () => {
      if (b.dataset.sure !== '1') { b.dataset.sure = '1'; b.textContent = 'Sure? Remove it'; return; }
      try { await ui.api('DELETE', '/plugins/' + enc(p.id)); paintList(body, await list(true)); } catch (e) { ui.toast(e.message, true); }
    });
    return b;
  }

  /* "Write a plugin": a plain code editor (monospace + line numbers) and the manifest fields */
  const STARTER = [
    '// Runs in a sealed box. `hoola` is the API, `command` the menu command she chose.',
    '// Every call returns a Promise. This one makes three squares on the current page.',
    'const page = await hoola.page();',
    'for (let i = 0; i < 3; i++) {',
    "  await hoola.create('RECT', page.id, {name: 'Square ' + (i + 1), x: i * 120, y: 0, w: 100, h: 100,",
    "    fills: [{type: 'solid', color: '#6E55F0', opacity: 1, visible: true}]});",
    '}',
    "hoola.notify('Made 3 squares.');",
    ''].join('\n');
  function slug(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'my-plugin'; }
  function write(pre) {
    if (!signedIn()) { ui.toast('Sign in to use plugins.'); return; }
    pre = pre || {};
    const m = pre.manifest || {}, has0 = p => (m.permissions || ['read', 'edit']).indexOf(p) >= 0;
    const field = (label, el) => h('label', {class: 'hdp-lab'}, h('span', {text: label}), el);
    const name = h('input', {class: 'hdp-in', type: 'text', maxlength: '80', value: m.name || 'My plugin', 'aria-label': 'Name'});
    const id = h('input', {class: 'hdp-in', type: 'text', maxlength: '64', value: m.id || slug(m.name || 'My plugin'), 'aria-label': 'Plugin id', spellcheck: 'false'});
    let idTouched = !!m.id;
    id.addEventListener('input', () => { idTouched = true; });
    name.addEventListener('input', () => { if (!idTouched) id.value = slug(name.value); });
    const version = h('input', {class: 'hdp-in', type: 'text', maxlength: '20', value: m.version || '1.0.0', 'aria-label': 'Version'});
    const desc = h('textarea', {class: 'hdp-in hdp-ta', rows: '2', maxlength: '500', 'aria-label': 'What it does', placeholder: 'What it does, in one or two lines'});
    desc.value = m.description || '';
    const pboxes = BASE.map(p => { const cb = h('input', {type: 'checkbox', checked: has0(p)}); cb.dataset.perm = p; return h('label', {class: 'hdp-check'}, cb, h('span', {text: words(p)})); });
    const hosts = h('input', {class: 'hdp-in', type: 'text', value: (m.permissions || []).filter(p => /^net:/.test(p)).map(p => p.slice(4)).join(', '), 'aria-label': 'Hosts it may talk to', placeholder: 'api.example.com, another.example.org', spellcheck: 'false'});
    const uiBox = h('input', {type: 'checkbox', checked: !!m.ui});
    const menu = h('textarea', {class: 'hdp-in hdp-ta mono', rows: '2', 'aria-label': 'Menu commands', spellcheck: 'false', placeholder: 'Run = run'});
    menu.value = (m.menu || [{label: 'Run', command: 'run'}]).map(it => it.label + ' = ' + it.command).join('\n');
    const ta = h('textarea', {class: 'hdp-src hdp-edit', spellcheck: 'false', autocapitalize: 'off', autocomplete: 'off', wrap: 'off', 'aria-label': 'Plugin code'});
    ta.value = typeof pre.code === 'string' ? pre.code : STARTER;
    const gut = h('pre', {class: 'hdp-gut', 'aria-hidden': 'true'});
    const lines = () => { const n = ta.value.split('\n').length; if (+gut.dataset.n !== n) { gut.dataset.n = n; let s = ''; for (let i = 1; i <= n; i++) s += (i > 1 ? '\n' : '') + i; gut.textContent = s; } gut.scrollTop = ta.scrollTop; };
    ta.addEventListener('input', lines); ta.addEventListener('scroll', () => { gut.scrollTop = ta.scrollTop; });
    ta.addEventListener('keydown', ev => { ev.stopPropagation(); if (ev.key === 'Tab' && !ev.shiftKey && !ev.ctrlKey && !ev.metaKey) { ev.preventDefault(); const a = ta.selectionStart, b = ta.selectionEnd; ta.value = ta.value.slice(0, a) + '  ' + ta.value.slice(b); ta.selectionStart = ta.selectionEnd = a + 2; lines(); } });
    const status = h('p', {class: 'hdp-status', role: 'status', 'aria-live': 'polite'});
    const collect = () => {
      const perms = pboxes.map(l => l.querySelector('input')).filter(cb => cb.checked).map(cb => cb.dataset.perm);
      for (const x of hosts.value.split(/[\s,]+/).map(v => v.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/\/.*$/, '')).filter(Boolean)) if (perms.indexOf('net:' + x) < 0) perms.push('net:' + x);
      const mm = menu.value.split('\n').map(l => l.trim()).filter(Boolean).map(l => { const i = l.indexOf('='); return i > 0 ? {label: l.slice(0, i).trim(), command: l.slice(i + 1).trim()} : {label: l, command: slug(l).replace(/-/g, '_').slice(0, 40)}; });
      return {id: id.value.trim(), name: name.value.trim(), version: version.value.trim() || '1.0.0', description: desc.value.trim(), permissions: perms, ui: !!uiBox.checked, menu: mm.length ? mm : [{label: 'Run', command: 'run'}]};
    };
    const save = h('button', {type: 'button', class: 'hd-btn pri', text: 'Save and install…', on: {click: () => {
      const man = collect(), probs = validate(man, ta.value);
      if (probs.length) { status.textContent = probs.join(' '); return; }
      review(man, ta.value, {mode: 'install'}).then(r => { if (!r.installed) write({manifest: man, code: ta.value}); });
    }}});
    ui.modal('hdp-dialog hdp-editor', 'Write a plugin', [head(pre.manifest ? 'Edit a plugin' : 'Write a plugin'),
      h('div', {class: 'hdp-body'},
        h('div', {class: 'hdp-grid'}, field('Name', name), field('Id', id), field('Version', version), field('Menu (one per line: Label = command)', menu)),
        field('What it does', desc),
        h('fieldset', {class: 'hdp-fs'}, h('legend', {text: 'It may'}), pboxes, field('Talk to these hosts (https only)', hosts), h('label', {class: 'hdp-check'}, uiBox, h('span', {text: 'Show its own panel'}))),
        h('div', {class: 'hdp-code'}, gut, ta),
        h('p', {class: 'hdp-note', text: 'The code is the body of an async function: use await hoola.… (selection, get, find, create, set, remove, move, exportPNG, exportSVG, fetch, storage, ui.show, notify, close).'})),
      h('div', {class: 'hdp-foot'}, status, h('button', {type: 'button', class: 'hd-btn', text: 'Cancel', on: {click: () => ui.closeModal()}}), save)]);
    const box = document.querySelector('.hdp-editor'); if (box) box.addEventListener('keydown', ev => { if (ev.key !== 'Escape') ev.stopPropagation(); });
    lines();
    ta.focus({preventScroll: true});
  }

  /* ---------------------------------------------------------------- where it is offered */
  function commands() {
    for (const p of st.list || []) {
      const m = p.manifest || {}, menu = m.menu || [];
      for (const it of menu) ui.command({id: 'plugin:' + p.id + ':' + it.command, label: 'Plugin: ' + (m.name || p.id) + (menu.length > 1 ? ' – ' + it.label : ''), group: 'Plugins',
        when: () => signedIn() && ready(known(p.id)) && !!(HD.app && HD.app.file), run: () => { run(p.id, it.command); }});
    }
  }
  ui.command({id: 'plugins', label: 'Plugins…', group: 'Plugins', when: signedIn, run: openManager});
  ui.command({id: 'plugin-write', label: 'Write a plugin…', group: 'Plugins', when: signedIn, run: () => write()});
  ui.command({id: 'plugin-stop', label: 'Stop the running plugin', group: 'Plugins', when: () => !!active, run: stop});
  ui.registerMenu('main', {label: 'Plugins', icon: 'spark', get sub() {
    const items = [{label: 'Manage plugins…', icon: 'sliders', run: openManager}, {label: 'Write a plugin…', icon: 'pen', run: () => write()}];
    const runs = [];
    for (const p of st.list || []) if (ready(p)) for (const it of (p.manifest.menu || []).slice(0, 8)) runs.push({label: (p.manifest.name || p.id) + ((p.manifest.menu || []).length > 1 ? ' – ' + it.label : ''), icon: 'play', run: () => { run(p.id, it.command); }});
    return runs.length ? runs.concat(['-'], items) : items;
  }, run: openManager});
  (function wire() {                                    /* hd-app.js loads after this file */
    if (!HD.app || !HD.app.on) { setTimeout(wire, 0); return; }
    HD.app.on('open', () => { if (signedIn()) list(true).catch(() => {}); });
    HD.app.on('close', () => { if (active) finish(active, false, ''); });
    if (HD.app.file && signedIn()) list(true).catch(() => {});
  })();

  HD.plugins = {install: install, run: run, list: list, open: openManager, write: write, review: review, approve: approve, stop: stop, validate: validate,
    words: words, config: config, METHODS: Object.keys(METHODS), FRAME_URL: FRAME_URL, get active() { return active ? {id: active.pid, name: active.name, command: active.command, state: active.state, edits: active.edits} : null; }};
})();

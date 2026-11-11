/* HOOLA DESIGN - tools (docs/HOOLA_DESIGN_PLAN.md, section 3: HD.tools).
   The canvas pointer wiring, every tool (move / frame / shapes / pen / pencil / text / hand / zoom / comment), the
   selection overlay with handles, snapping + smart guides, the in-place text editor, other people's cursors, and the
   editing actions (HD.tools.act: copy, group, align, order ...) the UI binds to keys and menus.
   Every document edit goes through HD.store inside a transaction; every pointer handler works in WORLD coordinates. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const DEG = Math.PI / 180;
  const DROP = {FRAME: 1, SECTION: 1, COMPONENT: 1};
  const HOLDS = {FRAME: 1, GROUP: 1, SECTION: 1, COMPONENT: 1, COMPONENT_SET: 1};
  const BASE_NAME = {RECT: 'Rectangle', ELLIPSE: 'Ellipse', LINE: 'Line', POLYGON: 'Polygon', STAR: 'Star', FRAME: 'Frame',
    GROUP: 'Group', VECTOR: 'Vector', TEXT: 'Text', SECTION: 'Section', COMPONENT: 'Component'};
  const ACCENT = '#6E55F0';

  /* ---------------------------------------------------------------- helpers */
  function prop(id, name) {
    const st = HD.store; if (st.prop) return st.prop(id, name);
    const n = st.get(id); if (!n) return undefined;
    if (n[name] !== undefined) return n[name];
    const d = st.defaults(n.type) || {}; return d[name];
  }
  function num(id, name, def) { const v = prop(id, name); return typeof v === 'number' && isFinite(v) ? v : (def === undefined ? 0 : def); }
  function typeOf(id) { const n = HD.store.get(id); return n ? n.type : ''; }
  function pageLike(id) { const t = typeOf(id); return !t || t === 'PAGE' || t === 'DOCUMENT'; }
  function wm(id) { return pageLike(id) ? HD.math.identity() : HD.store.worldMatrix(id); }
  function pinv(id) { return HD.math.inv(wm(HD.store.parent(id))); }
  function lin(m, dx, dy) { return [m[0] * dx + m[2] * dy, m[1] * dx + m[3] * dy]; }
  function size(id) { return [num(id, 'w', 100), typeOf(id) === 'LINE' ? 0 : num(id, 'h', 100)]; }
  function corners(id) { const m = wm(id), s = size(id), A = HD.math.apply; return [A(m, 0, 0), A(m, s[0], 0), A(m, s[0], s[1]), A(m, 0, s[1])]; }
  function centreW(id) { const s = size(id); return HD.math.apply(wm(id), s[0] / 2, s[1] / 2); }
  function aabb(id) { const c = corners(id); let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const p of c) { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); }
    return {x: x0, y: y0, w: x1 - x0, h: y1 - y0}; }
  function union(ids) { let r = null; for (const id of ids) { if (!HD.store.has(id)) continue; const b = aabb(id); r = r ? HD.math.rectUnion(r, b) : b; } return r; }
  function w2s(x, y) { return HD.render.worldToScreen(x, y); }
  function zoom() { return (HD.render.view && HD.render.view.zoom) || 1; }
  function r2(v) { return Math.round(v * 100) / 100; }
  function canEdit() { if (HD.tools.readOnly) return false; const f = HD.app && HD.app.file; if (f && f.role === 'view') return false; return !(HD.net && HD.net.role === 'view'); }
  function alive(ids) { return ids.filter(id => HD.store.has(id)); }
  function selIds() { return alive(HD.sel.ids || []); }
  function chain(id) { const out = []; let c = id, guard = 0; while (c && !pageLike(c) && guard++ < 500) { out.unshift(c); c = HD.store.parent(c); } return out; }
  function isInside(id, anc) { let c = HD.store.parent(id), g = 0; while (c && g++ < 500) { if (c === anc) return true; c = HD.store.parent(c); } return false; }
  /* the selection without nodes whose ancestor is selected too, in z order (bottom first) */
  function topLevel(ids) { const set = new Set(ids); const out = ids.filter(id => { let c = HD.store.parent(id), g = 0; while (c && g++ < 500) { if (set.has(c)) return false; c = HD.store.parent(c); } return true; });
    return sortZ(out); }
  function sortZ(ids) { const key = id => chain(id).map(c => String((HD.store.get(c) || {}).idx || '')); const keys = new Map(ids.map(id => [id, key(id)]));
    return ids.slice().sort((a, b) => { const ka = keys.get(a), kb = keys.get(b); for (let i = 0; i < Math.max(ka.length, kb.length); i++) { const x = ka[i] === undefined ? '' : ka[i], y = kb[i] === undefined ? '' : kb[i]; if (x !== y) return x < y ? -1 : 1; } return 0; }); }
  function pointIn(id, wx, wy) { const p = HD.math.apply(HD.math.inv(wm(id)), wx, wy), s = size(id); return p[0] >= 0 && p[1] >= 0 && p[0] <= s[0] && p[1] <= s[1]; }
  function containerAt(wx, wy, exclude) {
    let cur = HD.sel.page, guard = 0;
    /* D9b: on a big page only the layers under the point are looked at (HD.index; pointIn below still decides) */
    const cand = HD.index && HD.store.count() > 2000 ? new Set(HD.index.at(wx, wy, HD.sel.page, {tol: 0.001})) : null;
    while (guard++ < 200) {
      const kids = HD.store.children(cur); let found = null;
      for (let i = kids.length - 1; i >= 0; i--) { const k = kids[i]; if (exclude && exclude.has(k)) continue; if (cand && !cand.has(k)) continue; const n = HD.store.get(k);
        if (!n || !DROP[n.type] || prop(k, 'visible') === false || prop(k, 'locked')) continue;
        if (pointIn(k, wx, wy)) { found = k; break; } }
      if (!found) return cur; cur = found;
    }
    return cur;
  }
  function nextName(type) {
    const base = BASE_NAME[type] || 'Layer'; let max = 0, seen = 0; const re = new RegExp('^' + base + ' (\\d+)$');
    const stack = [HD.sel.page];
    while (stack.length && seen < 20000) { const id = stack.pop(); for (const k of HD.store.children(id)) { seen++; const n = HD.store.get(k); if (!n) continue;
      if (n.type === type) { const m = re.exec(n.name || ''); if (m) max = Math.max(max, +m[1]); } if (HOLDS[n.type]) stack.push(k); } }
    return base + ' ' + (max + 1);
  }
  function solid(color, opacity) { return {type: 'solid', color: color, opacity: opacity === undefined ? 1 : opacity, visible: true}; }

  /* A drag is many pointer moves but ONE undo step: HD.store.gesture() ... gestureEnd() merges every transaction in
     between into one step (ops still go out on each move, so other people see the drag live). Without that API the
     previous step of the same drag is taken back and the whole change applied again (fn is always absolute). */
  let localChanges = 0;
  function Gesture(label) { this.label = label; this.started = false; this.mark = 0; }
  Gesture.prototype.apply = function (fn) {
    const st = HD.store;
    if (st.gesture) { if (!this.started) { st.gesture(); this.started = true; this.mark = localChanges; } st.tx(this.label, fn); return; }
    if (this.started) { st.undo(); this.started = false; }
    const before = localChanges; st.tx(this.label, fn); this.started = localChanges !== before;
  };
  Gesture.prototype.end = function () { if (this.started && HD.store.gestureEnd) HD.store.gestureEnd(); this.started = false; };
  Gesture.prototype.cancel = function () { const st = HD.store; if (!this.started) return; this.started = false;
    if (st.gesture) { st.gestureEnd(); if (localChanges !== this.mark) st.undo(); } else st.undo(); };

  /* ---------------------------------------------------------------- view */
  const View = {
    sem: '',
    detect() { const R = HD.render, v = R.view; if (!v) return 'offset'; if (this.sem) return this.sem;
      if (!v.x && !v.y) return 'offset';
      const s = R.worldToScreen(0, 0); this.sem = (Math.abs(s[0] - v.x) < 0.01 && Math.abs(s[1] - v.y) < 0.01) ? 'offset' : 'origin'; return this.sem; },
    /* the view that shows world point (wx, wy) at screen point (sx, sy) with this zoom */
    at(z, wx, wy, sx, sy) { return this.detect() === 'offset' ? {x: sx - wx * z, y: sy - wy * z, zoom: z} : {x: wx - sx / z, y: wy - sy / z, zoom: z}; },
    panBy(dx, dy) { const R = HD.render, w = R.screenToWorld(0, 0); R.setView(this.at(zoom(), w[0], w[1], dx, dy)); changed(); },
    zoomAt(sx, sy, z, animate) { const R = HD.render, w = R.screenToWorld(sx, sy); z = Math.max(0.02, Math.min(256, z)); R.setView(this.at(z, w[0], w[1], sx, sy), animate); changed(); },
    centre() { const c = HD.tools.canvas; return c ? [c.clientWidth / 2, c.clientHeight / 2] : [400, 300]; },
    zoomTo(z, animate) { const c = this.centre(); this.zoomAt(c[0], c[1], z, animate); },
    zoomBy(f) { this.zoomTo(zoom() * f, true); },
    fit(ids) { HD.render.zoomToFit(ids && ids.length ? ids : undefined); changed(); },
    rect(r) { const c = HD.tools.canvas; if (!c || !r || !r.w || !r.h) return; const z = Math.max(0.02, Math.min(256, Math.min(c.clientWidth / r.w, c.clientHeight / r.h) * 0.9));
      HD.render.setView(this.at(z, r.x + r.w / 2, r.y + r.h / 2, c.clientWidth / 2, c.clientHeight / 2), true); changed(); }
  };
  const viewSubs = [];
  function changed() { for (const f of viewSubs) { try { f(); } catch (e) { /* a listener must not stop the view */ } } }

  /* ---------------------------------------------------------------- registry */
  const defs = {}; let curName = '', lastTool = 'move'; const toolSubs = [];
  const state = {hover: null, drag: null, guides: [], gaps: [], marquee: null, draft: null, dropInto: null, pen: null, spaceDown: false, panning: null};
  HD.tools = {
    canvas: null, host: null, readOnly: false, view: View, snapOn: true,
    register(name, def) { defs[name] = def || {}; },
    set(name) {
      if (!defs[name]) return; if (!canEdit() && !{move: 1, hand: 1, zoom: 1, comment: 1}[name]) name = 'move';
      if (HD.tools.panOnly) name = 'hand';
      if (curName === name) return;
      const old = defs[curName]; if (old && old.leave) old.leave();
      lastTool = curName || 'move'; curName = name; const d = defs[name]; if (d.enter) d.enter();
      setCursor(d.cursor || 'default'); redraw(); for (const f of toolSubs) f(name);
    },
    get current() { return curName; },
    get def() { return defs[curName]; },
    list() { return Object.keys(defs); },
    onChange(fn) { toolSubs.push(fn); },
    onView(fn) { viewSubs.push(fn); },
    attach: attach, key: key, redraw: redraw,
    u: {prop, num, typeOf, wm, corners, aabb, union, topLevel, sortZ, chain, canEdit, containerAt, nextName, solid, Gesture, pageLike, isInside, scalePath, selIds},
    state: state
  };
  function setCursor(c) { if (HD.tools.canvas) HD.tools.canvas.style.cursor = c; }
  function redraw() { if (HD.render && HD.render.invalidate) HD.render.invalidate(); }

  /* ---------------------------------------------------------------- pointer wiring */
  function mkEvent(ev) {
    const c = HD.tools.canvas, r = c.getBoundingClientRect(), sx = ev.clientX - r.left, sy = ev.clientY - r.top, w = HD.render.screenToWorld(sx, sy);
    const e = {x: w[0], y: w[1], sx: sx, sy: sy, shift: !!ev.shiftKey, alt: !!ev.altKey, mod: !!(ev.ctrlKey || ev.metaKey), button: ev.button || 0, raw: ev};
    let hit; Object.defineProperty(e, 'target', {enumerable: true, get() { if (hit === undefined) hit = HD.render.hitTest(w[0], w[1], {deep: false}) || null; return hit; }});
    return e;
  }
  let lastPres = 0, lastPtr = null;
  function presence(e) {
    if (!HD.net || !HD.net.sendPresence) return; const now = Date.now(); if (e) lastPtr = e; if (now - lastPres < 40 || !lastPtr) return; lastPres = now;
    const v = HD.render.view || {}; try { HD.net.sendPresence({x: r2(lastPtr.x), y: r2(lastPtr.y), page: HD.sel.page, sel: (HD.sel.ids || []).slice(0, 200), vp: [v.x, v.y, v.zoom]}); } catch (err) { /* offline */ }
  }
  const touches = new Map(); let pinch = null;
  function attach(canvas, host) {
    HD.tools.canvas = canvas; HD.tools.host = host; canvas.style.touchAction = 'none';
    canvas.addEventListener('pointerdown', ev => {
      if (ev.pointerType === 'touch') { touches.set(ev.pointerId, {x: ev.clientX, y: ev.clientY}); if (touches.size === 2) { cancelDrag(); pinch = pinchState(); return; } }
      if (TextEdit.el && ev.target !== TextEdit.el) TextEdit.commit();
      canvas.focus({preventScroll: true}); try { canvas.setPointerCapture(ev.pointerId); } catch (e) { /* synthetic */ }
      const e = mkEvent(ev);
      if (ev.button === 1 || (ev.button === 0 && state.spaceDown) || HD.tools.panOnly) { state.panning = {sx: ev.clientX, sy: ev.clientY}; setCursor('grabbing'); ev.preventDefault(); return; }
      if (ev.button === 2) return;
      state.down = true; const d = defs[curName]; if (d && d.down) d.down(e); redraw();
    });
    canvas.addEventListener('pointermove', ev => {
      if (ev.pointerType === 'touch' && touches.has(ev.pointerId)) { touches.set(ev.pointerId, {x: ev.clientX, y: ev.clientY}); if (pinch && touches.size === 2) { doPinch(); return; } }
      if (state.panning) { View.panBy(ev.clientX - state.panning.sx, ev.clientY - state.panning.sy); state.panning.sx = ev.clientX; state.panning.sy = ev.clientY; return; }
      const e = mkEvent(ev); presence(e); const d = defs[curName]; if (d && d.move) d.move(e);
    });
    const up = ev => {
      if (ev.pointerType === 'touch') { touches.delete(ev.pointerId); if (pinch) { if (touches.size < 2) pinch = null; return; } }
      try { canvas.releasePointerCapture(ev.pointerId); } catch (e) { /* not captured */ }
      if (state.panning) { state.panning = null; setCursor(state.spaceDown || HD.tools.panOnly ? 'grab' : ((defs[curName] || {}).cursor || 'default')); return; }
      if (!state.down) return; state.down = false; const d = defs[curName]; if (d && d.up) d.up(mkEvent(ev)); redraw();
    };
    canvas.addEventListener('pointerup', up); canvas.addEventListener('pointercancel', up);
    canvas.addEventListener('pointerleave', () => { if (!state.down && state.hover) { state.hover = null; redraw(); } });
    canvas.addEventListener('dblclick', ev => { const d = defs[curName]; if (d && d.dbl) d.dbl(mkEvent(ev)); redraw(); });
    canvas.addEventListener('wheel', ev => {
      ev.preventDefault(); const r = canvas.getBoundingClientRect(), sx = ev.clientX - r.left, sy = ev.clientY - r.top;
      let dx = ev.deltaX, dy = ev.deltaY; if (ev.deltaMode === 1) { dx *= 16; dy *= 16; }
      if (ev.ctrlKey || ev.metaKey) { const k = Math.exp(-Math.max(-60, Math.min(60, dy)) * 0.01); View.zoomAt(sx, sy, zoom() * k); }
      else { if (ev.shiftKey && !dx) { dx = dy; dy = 0; } View.panBy(-dx, -dy); }
      if (TextEdit.el) TextEdit.place();
    }, {passive: false});
    canvas.addEventListener('contextmenu', ev => { ev.preventDefault(); const e = mkEvent(ev);
      if (canEdit() || true) { const t = resolveHit(HD.render.hitTest(e.x, e.y, {deep: true}), e); if (t && !HD.sel.has(t)) HD.sel.set([t]); }
      if (HD.ui && HD.ui.contextMenu) HD.ui.contextMenu(ev.clientX, ev.clientY, e); });
    cancelDrag(); state.hover = null; state.scope = null; state.pen = null; touches.clear(); pinch = null;
    if (!wiredOnce) { wiredOnce = true;   /* the canvas is new for every file; these listen for the life of the page */
      window.addEventListener('keydown', ev => { if (ev.code === 'Space' && !typing(ev) && !state.spaceDown && HD.tools.canvas) { state.spaceDown = true; if (!state.down) setCursor('grab'); } });
      window.addEventListener('keyup', ev => { if (ev.code === 'Space') { state.spaceDown = false; if (!state.panning) setCursor((defs[curName] || {}).cursor || 'default'); } });
      window.addEventListener('blur', () => { state.spaceDown = false; });
      HD.render.addOverlay(drawOverlay);
      if (HD.store.on) HD.store.on('change', ch => { if (!ch || !ch.remote) localChanges++; if (TextEdit.el) TextEdit.place(); });
      if (HD.sel.on) HD.sel.on('change', () => { presence(); redraw(); });
      if (HD.net && HD.net.on) HD.net.on('presence', redraw); }
    if (curName === 'move') setCursor('default'); else { curName = ''; HD.tools.set('move'); }
  }
  let wiredOnce = false;
  function typing(ev) { const t = ev.target; return !!(t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)); }
  function pinchState() { const p = Array.from(touches.values()), r = HD.tools.canvas.getBoundingClientRect();
    return {d: Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y) || 1, mx: (p[0].x + p[1].x) / 2 - r.left, my: (p[0].y + p[1].y) / 2 - r.top, z: zoom()}; }
  function doPinch() { const n = pinchState(); View.panBy(n.mx - pinch.mx, n.my - pinch.my); View.zoomAt(n.mx, n.my, pinch.z * n.d / pinch.d); pinch.mx = n.mx; pinch.my = n.my; }
  function cancelDrag() { if (state.drag && state.drag.gesture) state.drag.gesture.cancel(); state.drag = null; state.marquee = null; state.draft = null; state.guides = []; state.gaps = []; state.down = false; state.panning = null; }
  function key(ev) { const d = defs[curName]; if (d && d.key) return d.key(ev); return false; }

  /* ---------------------------------------------------------------- hit testing for selection */
  function resolveHit(deep, e) {
    if (!deep || !HD.store.has(deep)) return null;
    const ch = chain(deep); if (!ch.length) return null;
    for (const c of ch) if (prop(c, 'locked')) return null;
    if (e && e.mod) return deep;
    for (const c of ch) if (HD.sel.has(c)) return c;
    const sel = selIds();
    if (sel.length) { const p = HD.store.parent(sel[0]), i = ch.indexOf(p); if (i >= 0 && i + 1 < ch.length) return ch[i + 1]; }
    if (state.scope) { const i = ch.indexOf(state.scope); if (i >= 0 && i + 1 < ch.length) return ch[i + 1]; }
    const t = typeOf(ch[0]);
    if (ch.length > 1 && DROP[t]) return ch[1];
    return ch[0];
  }

  /* ---------------------------------------------------------------- selection box + handles (screen space) */
  function selBox() {
    const ids = selIds(); if (!ids.length) return null;
    if (ids.length === 1) { const c = corners(ids[0]).map(p => w2s(p[0], p[1])); const line = typeOf(ids[0]) === 'LINE';
      return {pts: c, single: ids[0], line: line, ang: Math.atan2(c[1][1] - c[0][1], c[1][0] - c[0][0])}; }
    const u = union(ids); if (!u) return null;
    const a = w2s(u.x, u.y), b = w2s(u.x + u.w, u.y + u.h);
    return {pts: [a, [b[0], a[1]], b, [a[0], b[1]]], single: null, ang: 0, world: u};
  }
  const HANDLES = [[-1, -1], [0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0]];
  function handlePos(box, h) { const p = box.pts, mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
    const cx = h[0], cy = h[1]; const top = cx < 0 ? p[0] : cx > 0 ? p[1] : mid(p[0], p[1]), bot = cx < 0 ? p[3] : cx > 0 ? p[2] : mid(p[3], p[2]);
    return cy < 0 ? top : cy > 0 ? bot : mid(top, bot); }
  function segDist(p, a, b) { const vx = b[0] - a[0], vy = b[1] - a[1], l2 = vx * vx + vy * vy; let t = l2 ? ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / l2 : 0; t = Math.max(0, Math.min(1, t));
    return Math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy); }
  function inQuad(p, q) { let s = 0; for (let i = 0; i < 4; i++) { const a = q[i], b = q[(i + 1) % 4], c = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]); if (Math.abs(c) < 1e-9) continue; if (!s) s = Math.sign(c); else if (Math.sign(c) !== s) return false; } return true; }
  function handleAt(sx, sy) {
    if (!canEdit()) return null; const box = selBox(); if (!box) return null; const p = [sx, sy];
    if (box.line) { for (const h of [[-1, 0], [1, 0]]) { const q = handlePos(box, h); if (Math.hypot(q[0] - sx, q[1] - sy) <= 8) return {kind: 'line', h: h, box: box}; } return null; }
    const wpx = Math.hypot(box.pts[1][0] - box.pts[0][0], box.pts[1][1] - box.pts[0][1]), hpx = Math.hypot(box.pts[3][0] - box.pts[0][0], box.pts[3][1] - box.pts[0][1]);
    for (const h of HANDLES) { if (!h[0] || !h[1]) continue; const q = handlePos(box, h); if (Math.hypot(q[0] - sx, q[1] - sy) <= 7) return {kind: 'resize', h: h, box: box}; }
    const edges = [[[0, -1], 0, 1], [[1, 0], 1, 2], [[0, 1], 3, 2], [[-1, 0], 0, 3]];
    for (const ed of edges) { const along = ed[0][0] ? hpx : wpx; if (along < 14) continue; if (segDist(p, box.pts[ed[1]], box.pts[ed[2]]) <= 5) return {kind: 'resize', h: ed[0], box: box}; }
    if (!inQuad(p, box.pts)) for (const h of HANDLES) { if (!h[0] || !h[1]) continue; const q = handlePos(box, h); const d = Math.hypot(q[0] - sx, q[1] - sy); if (d > 7 && d <= 24) return {kind: 'rotate', h: h, box: box}; }
    return null;
  }
  const RES_CUR = ['ew-resize', 'nwse-resize', 'ns-resize', 'nesw-resize'];
  function handleCursor(hd) {
    if (hd.kind === 'rotate') return ROT_CUR;
    if (hd.kind === 'line') return 'move';
    const a = Math.atan2(hd.h[1], hd.h[0]) + hd.box.ang; let i = Math.round(a / (Math.PI / 4)); i = ((i % 4) + 4) % 4; return RES_CUR[i];
  }
  const ROT_CUR = 'url("data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 22 22"><path d="M5 14a7 7 0 0 1 12-5" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round"/><path d="M5 14a7 7 0 0 1 12-5" fill="none" stroke="#111" stroke-width="1.6" stroke-linecap="round"/><path d="M17.6 4.4v5.2h-5.2z" fill="#111" stroke="#fff" stroke-width="1"/><path d="M2.2 12.6l2.8 4.4 2.8-4.4z" fill="#111" stroke="#fff" stroke-width="1"/></svg>') + '") 11 11, crosshair';

  /* ---------------------------------------------------------------- snapping */
  function snapCands(excludeIds, parentId) {
    const ex = new Set(excludeIds), out = []; const par = parentId || HD.sel.page;
    let kids = HD.store.children(par); let n = 0;
    if (kids.length > 400 && HD.index && HD.tools.canvas) {   /* D9b: many siblings - the ones in view, not the first 400 */
      const cv = HD.tools.canvas, a = HD.render.screenToWorld(0, 0), b = HD.render.screenToWorld(cv.clientWidth, cv.clientHeight);
      kids = HD.index.query({x: a[0], y: a[1], w: b[0] - a[0], h: b[1] - a[1]}, HD.sel.page).filter(k => HD.store.parent(k) === par);
    }
    for (const k of kids) { if (ex.has(k) || prop(k, 'visible') === false) continue; if (++n > 400) break; out.push(aabb(k)); }
    if (!pageLike(par)) out.push(Object.assign({parent: true}, aabb(par)));
    if (HD.tools.snapExtra) { try { for (const c of HD.tools.snapExtra(par) || []) out.push(c); } catch (e) { /* guides are optional */ } }   /* ruler guides (hd-vector.js) */
    return out;
  }
  function snapAxis(vals, cands, axis, thr) {
    let best = null;
    for (const c of cands) { const cs = axis === 'x' ? [c.x, c.x + c.w / 2, c.x + c.w] : [c.y, c.y + c.h / 2, c.y + c.h];
      for (const v of vals) for (const t of cs) { const d = t - v; if (Math.abs(d) <= thr && (!best || Math.abs(d) < Math.abs(best.d))) best = {d: d, at: t, c: c}; } }
    return best;
  }
  /* move snapping: returns the corrected delta and fills state.guides / state.gaps */
  function snapMove(box, cands) {
    const thr = 5 / zoom(); let dx = 0, dy = 0; state.guides = []; state.gaps = [];
    const sx = snapAxis([box.x, box.x + box.w / 2, box.x + box.w], cands, 'x', thr), sy = snapAxis([box.y, box.y + box.h / 2, box.y + box.h], cands, 'y', thr);
    if (sx) dx = sx.d; else { const g = gapSnap(box, cands, 'x', thr); if (g) dx = g.d; }
    if (sy) dy = sy.d; else { const g = gapSnap(box, cands, 'y', thr); if (g) dy = g.d; }
    const nb = {x: box.x + dx, y: box.y + dy, w: box.w, h: box.h};
    guidesFor(nb, cands); if (!sx || !sy) gapHints(nb, cands, !sx, !sy);
    return [dx, dy];
  }
  function guidesFor(nb, cands) {
    const eps = 0.01;
    for (const c of cands) {
      for (const t of [c.x, c.x + c.w / 2, c.x + c.w]) for (const v of [nb.x, nb.x + nb.w / 2, nb.x + nb.w]) if (Math.abs(t - v) < eps) state.guides.push({x: t, a: Math.min(nb.y, c.y), b: Math.max(nb.y + nb.h, c.y + c.h)});
      for (const t of [c.y, c.y + c.h / 2, c.y + c.h]) for (const v of [nb.y, nb.y + nb.h / 2, nb.y + nb.h]) if (Math.abs(t - v) < eps) state.guides.push({y: t, a: Math.min(nb.x, c.x), b: Math.max(nb.x + nb.w, c.x + c.w)});
    }
    if (state.guides.length > 12) state.guides.length = 12;
  }
  function neighbours(box, cands, axis) {
    const X = axis === 'x', lo = [], hi = [];
    for (const c of cands) { if (c.parent) continue; const overlap = X ? (c.y < box.y + box.h && c.y + c.h > box.y) : (c.x < box.x + box.w && c.x + c.w > box.x); if (!overlap) continue;
      const cs = X ? c.x : c.y, ce = cs + (X ? c.w : c.h), bs = X ? box.x : box.y, be = bs + (X ? box.w : box.h);
      if (ce <= bs + 6 / zoom() && cs < bs) lo.push({s: cs, e: ce, c: c}); else if (cs >= be - 6 / zoom()) hi.push({s: cs, e: ce, c: c}); }
    lo.sort((a, b) => b.e - a.e); hi.sort((a, b) => a.s - b.s); return {lo: lo, hi: hi};
  }
  function gapSnap(box, cands, axis, thr) {
    const n = neighbours(box, cands, axis), bs = axis === 'x' ? box.x : box.y, bl = axis === 'x' ? box.w : box.h; let best = null;
    const tryT = t => { const d = t - bs; if (Math.abs(d) <= thr && (!best || Math.abs(d) < Math.abs(best.d))) best = {d: d}; };
    if (n.lo.length && n.hi.length) tryT(n.lo[0].e + (n.hi[0].s - n.lo[0].e - bl) / 2);
    if (n.lo.length > 1 && n.lo[0].s - n.lo[1].e > 0) tryT(n.lo[0].e + (n.lo[0].s - n.lo[1].e));
    if (n.hi.length > 1 && n.hi[1].s - n.hi[0].e > 0) tryT(n.hi[0].s - (n.hi[1].s - n.hi[0].e) - bl);
    return best;
  }
  function gapHints(nb, cands, doX, doY) {
    for (const axis of ['x', 'y']) { if ((axis === 'x' && !doX) || (axis === 'y' && !doY)) continue;
      const X = axis === 'x', n = neighbours(nb, cands, axis), bs = X ? nb.x : nb.y, be = bs + (X ? nb.w : nb.h), mid = X ? nb.y + nb.h / 2 : nb.x + nb.w / 2, eq = (a, b) => Math.abs(a - b) < 0.01 && a > 0;
      const add = (s, e) => state.gaps.push({axis: axis, s: s, e: e, at: mid});
      if (n.lo.length && n.hi.length && eq(bs - n.lo[0].e, n.hi[0].s - be)) { add(n.lo[0].e, bs); add(be, n.hi[0].s); }
      else if (n.lo.length > 1 && eq(bs - n.lo[0].e, n.lo[0].s - n.lo[1].e)) { add(n.lo[1].e, n.lo[0].s); add(n.lo[0].e, bs); }
      else if (n.hi.length > 1 && eq(n.hi[0].s - be, n.hi[1].s - n.hi[0].e)) { add(be, n.hi[0].s); add(n.hi[0].e, n.hi[1].s); } }
  }
  function snapPoint(x, y, cands, wantX, wantY) {
    const thr = 5 / zoom(); state.guides = []; let nx = x, ny = y;
    if (wantX !== false) { const s = snapAxis([x], cands, 'x', thr); if (s) { nx = s.at; state.guides.push({x: s.at, a: Math.min(y, s.c.y), b: Math.max(y, s.c.y + s.c.h)}); } }
    if (wantY !== false) { const s = snapAxis([y], cands, 'y', thr); if (s) { ny = s.at; state.guides.push({y: s.at, a: Math.min(x, s.c.x), b: Math.max(x, s.c.x + s.c.w)}); } }
    return [nx, ny];
  }
  function snapping(e) { return HD.tools.snapOn && !(e && e.mod); }

  /* ---------------------------------------------------------------- vector path helpers */
  function scalePath(d, fx, fy) {
    if (!d || (fx === 1 && fy === 1)) return d;
    const re = /([MmLlHhVvCcSsQqTtAaZz])|(-?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)/g; let m, cmd = '', k = 0; const segs = [];
    while ((m = re.exec(d))) {
      if (m[1]) { cmd = m[1]; k = 0; segs.push({c: cmd, n: []}); continue; }
      if (!segs.length) continue; let v = parseFloat(m[2]); const c = cmd.toUpperCase();
      if (c === 'H') v *= fx; else if (c === 'V') v *= fy;
      else if (c === 'A') { const i = k % 7; if (i === 0) v *= Math.abs(fx); else if (i === 1) v *= Math.abs(fy); else if (i === 5) v *= fx; else if (i === 6) v *= fy; }
      else v *= (k % 2 === 0) ? fx : fy;
      k++; segs[segs.length - 1].n.push(String(c === 'A' && (k - 1) % 7 >= 2 && (k - 1) % 7 <= 4 ? parseFloat(m[2]) : r2(v)));
    }
    return segs.map(sg => sg.c + sg.n.join(' ')).join('');
  }
  function ptsToPath(pts, closed) {
    if (!pts.length) return ''; let d = 'M' + r2(pts[0].x) + ' ' + r2(pts[0].y);
    const seg = (a, b) => { if (a.o || b.i) { const c1 = a.o || a, c2 = b.i || b; d += 'C' + r2(c1.x) + ' ' + r2(c1.y) + ' ' + r2(c2.x) + ' ' + r2(c2.y) + ' ' + r2(b.x) + ' ' + r2(b.y); } else d += 'L' + r2(b.x) + ' ' + r2(b.y); };
    for (let i = 1; i < pts.length; i++) seg(pts[i - 1], pts[i]);
    if (closed) { seg(pts[pts.length - 1], pts[0]); d += 'Z'; }
    return d;
  }
  function pathBounds(pts, closed) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity; const add = (x, y) => { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); };
    const seg = (a, b) => { if (a.o || b.i) { const c1 = a.o || a, c2 = b.i || b; for (let t = 0; t <= 1.0001; t += 1 / 24) { const u = 1 - t;
      add(u * u * u * a.x + 3 * u * u * t * c1.x + 3 * u * t * t * c2.x + t * t * t * b.x, u * u * u * a.y + 3 * u * u * t * c1.y + 3 * u * t * t * c2.y + t * t * t * b.y); } } else { add(a.x, a.y); add(b.x, b.y); } };
    if (pts.length === 1) add(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) seg(pts[i - 1], pts[i]); if (closed && pts.length > 1) seg(pts[pts.length - 1], pts[0]);
    return {x: x0, y: y0, w: x1 - x0, h: y1 - y0};
  }
  /* world-space bezier points -> a VECTOR node in its parent's space */
  function createVector(wpts, closed, extra) {
    if (wpts.length < 2) return null;
    const anchor = wpts[0], parent = containerAt(anchor.x, anchor.y), inv = HD.math.inv(wm(parent));
    const tp = p => { const q = HD.math.apply(inv, p.x, p.y); return {x: q[0], y: q[1]}; };
    const lp = wpts.map(p => { const o = tp(p); if (p.i) o.i = tp(p.i); if (p.o) o.o = tp(p.o); return o; });
    const b = pathBounds(lp, closed), sh = p => ({x: p.x - b.x, y: p.y - b.y});
    const rel = lp.map(p => { const o = sh(p); if (p.i) o.i = sh(p.i); if (p.o) o.o = sh(p.o); return o; });
    let id = null;
    HD.store.tx('Draw vector', () => {
      id = HD.store.create('VECTOR', parent, Object.assign({name: nextName('VECTOR'), x: r2(b.x), y: r2(b.y), w: Math.max(r2(b.w), 0.01), h: Math.max(r2(b.h), 0.01), path: ptsToPath(rel, closed),
        fills: closed ? [solid('#D9D9D9')] : [], strokes: [solid('#1A1A1F')], strokeWeight: closed ? 1 : 2, strokeCap: 'round', strokeJoin: 'round'}, extra || {}));
    });
    return id;
  }
  function simplify(pts, tol) {
    if (pts.length < 3) return pts.slice(); const keep = new Uint8Array(pts.length); keep[0] = keep[pts.length - 1] = 1; const stack = [[0, pts.length - 1]];
    while (stack.length) { const pr = stack.pop(), a = pts[pr[0]], b = pts[pr[1]]; let md = 0, mi = -1;
      for (let i = pr[0] + 1; i < pr[1]; i++) { const d = segDist([pts[i].x, pts[i].y], [a.x, a.y], [b.x, b.y]); if (d > md) { md = d; mi = i; } }
      if (md > tol && mi > 0) { keep[mi] = 1; stack.push([pr[0], mi], [mi, pr[1]]); } }
    return pts.filter((p, i) => keep[i]);
  }
  function smooth(pts) {   /* Catmull-Rom through the kept points -> cubic handles */
    const n = pts.length, out = pts.map(p => ({x: p.x, y: p.y})); if (n < 3) return out;
    for (let i = 0; i < n; i++) { const p0 = pts[Math.max(0, i - 1)], p2 = pts[Math.min(n - 1, i + 1)], p = pts[i], tx = (p2.x - p0.x) / 6, ty = (p2.y - p0.y) / 6;
      if (i > 0) out[i].i = {x: p.x - tx, y: p.y - ty}; if (i < n - 1) out[i].o = {x: p.x + tx, y: p.y + ty}; }
    return out;
  }

  /* ---------------------------------------------------------------- gestures: move / resize / rotate */
  function snapshot(id) {
    const s = size(id), n = HD.store.get(id) || {}; const o = {id: id, type: n.type, x: num(id, 'x'), y: num(id, 'y'), w: s[0], h: s[1], rot: num(id, 'rot'), parent: HD.store.parent(id),
      flipH: !!prop(id, 'flipH'), flipV: !!prop(id, 'flipV'), path: n.path, pinv: pinv(id), cw: centreW(id), box: aabb(id), auto: prop(id, 'autoResize')};
    if (n.type === 'GROUP') o.kids = HD.store.children(id).map(snapshot);
    return o;
  }
  function scaleKids(kids, fx, fy) {
    for (const k of kids) { const p = {x: r2(k.x * fx), y: r2(k.y * fy), w: Math.max(0.01, r2(k.w * fx))}; if (k.type !== 'LINE') p.h = Math.max(0.01, r2(k.h * fy));
      if (k.type === 'VECTOR' && k.path) p.path = scalePath(k.path, fx, fy);
      HD.store.set(k.id, p); if (k.kids) scaleKids(k.kids, fx, fy); }
  }
  function startMove(e, ids) {
    const top = topLevel(ids).filter(id => !prop(id, 'locked')); if (!top.length) return null;
    return {mode: 'move', ids: top, items: top.map(snapshot), sx: e.sx, sy: e.sy, wx: e.x, wy: e.y, box: union(top), gesture: new Gesture('Move'), moved: false, set: new Set(top)};
  }
  function doMove(d, e) {
    let dx = e.x - d.wx, dy = e.y - d.wy;
    if (e.shift) { if (Math.abs(dx) > Math.abs(dy)) dy = 0; else dx = 0; }
    const ex = new Set(); for (const id of d.ids) { ex.add(id); }
    let target = containerAt(e.x, e.y, ex);
    const firstPar = d.items[0].parent; if (typeOf(firstPar) === 'GROUP' && (target === HD.sel.page || isInside(firstPar, target) || target === firstPar)) { if (pointIn(firstPar, e.x, e.y) || d.items.every(it => it.parent === firstPar)) target = firstPar; }
    const lay = prop(target, 'layout'), auto = !!(lay && lay.mode && lay.mode !== 'none');
    state.guides = []; state.gaps = [];
    if (!auto && snapping(e)) { const s = snapMove({x: d.box.x + dx, y: d.box.y + dy, w: d.box.w, h: d.box.h}, snapCands(d.ids, target)); dx += s[0]; dy += s[1]; }
    state.dropInto = target !== HD.sel.page && target !== firstPar ? target : null;
    const tinv = HD.math.inv(wm(target));
    d.gesture.apply(() => {
      for (const it of d.items) {
        if (!HD.store.has(it.id)) continue;
        const flow = auto && prop(it.id, 'layoutPos') !== 'absolute';
        if (flow) { const before = flowBefore(target, lay, e, d.set), sib = HD.store.children(target); let k = sib.indexOf(it.id) + 1; while (k > 0 && k < sib.length && d.set.has(sib[k])) k++;
          if (HD.store.parent(it.id) !== target || (sib[k] || null) !== before) HD.store.move([it.id], target, before); continue; }
        if (HD.store.parent(it.id) !== target) HD.store.move([it.id], target, null);
        const c = HD.math.apply(tinv, it.cw[0] + dx, it.cw[1] + dy), keepInt = !it.rot;
        const nx = c[0] - it.w / 2, ny = c[1] - it.h / 2;
        HD.store.set(it.id, {x: keepInt ? Math.round(nx) : r2(nx), y: keepInt ? Math.round(ny) : r2(ny)});
      }
    });
  }
  function flowBefore(parent, lay, e, moving) {
    const kids = HD.store.children(parent).filter(k => !moving.has(k) && prop(k, 'layoutPos') !== 'absolute'), X = lay.mode === 'h';
    for (const k of kids) { const b = aabb(k), mid = X ? b.x + b.w / 2 : b.y + b.h / 2; if ((X ? e.x : e.y) < mid) return k; }
    return null;
  }
  function startResize(e, hd) {
    const ids = topLevel(selIds()).filter(id => !prop(id, 'locked')); if (!ids.length) return null;
    const hp = handlePos(hd.box, hd.h), hw = HD.render.screenToWorld(hp[0], hp[1]);
    return {mode: 'resize', h: hd.h, ids: ids, items: ids.map(snapshot), single: ids.length === 1, box: union(ids), off: [hw[0] - e.x, hw[1] - e.y], gesture: new Gesture('Resize'), cands: snapCands(ids, HD.store.parent(ids[0]))};
  }
  function doResize(d, e) {
    let px = e.x + d.off[0], py = e.y + d.off[1]; const hx = d.h[0], hy = d.h[1]; state.guides = [];
    const wa = d.single ? Math.abs(worldAng(d.items[0].id)) % 180 : 0, flat = wa < 0.01 || Math.abs(wa - 180) < 0.01, quarter = Math.abs(wa - 90) < 0.01;
    if (snapping(e) && (flat || quarter)) { const s = snapPoint(px, py, d.cands, quarter ? !!hy : !!hx, quarter ? !!hx : !!hy); px = s[0]; py = s[1]; }
    if (d.single) { resizeOne(d, e, px, py); return; }
    resizeMany(d, e, px, py);
  }
  function resizeOne(d, e, px, py) {
    {
      const it = d.items[0], th = it.rot * DEG, cos = Math.cos(th), sin = Math.sin(th), hx = d.h[0] * (it.flipH ? -1 : 1), hy = d.h[1] * (it.flipV ? -1 : 1);
      const pp = HD.math.apply(it.pinv, px, py), cx = it.x + it.w / 2, cy = it.y + it.h / 2;
      const ux = (pp[0] - cx) * cos + (pp[1] - cy) * sin, uy = -(pp[0] - cx) * sin + (pp[1] - cy) * cos;   /* pointer in the node's own axes */
      let x0 = -it.w / 2, x1 = it.w / 2, y0 = -it.h / 2, y1 = it.h / 2;
      if (hx > 0) x1 = ux; else if (hx < 0) x0 = ux; if (hy > 0) y1 = uy; else if (hy < 0) y0 = uy;
      if (e.alt) { if (hx > 0) x0 = -ux; else if (hx < 0) x1 = -ux; if (hy > 0) y0 = -uy; else if (hy < 0) y1 = -uy; }
      let w = x1 - x0, h = y1 - y0;
      if (e.shift && it.w && it.h) { const ratio = it.w / it.h;
        if (hx && hy) { if (Math.abs(w) / ratio > Math.abs(h)) h = Math.sign(h || 1) * Math.abs(w) / ratio; else w = Math.sign(w || 1) * Math.abs(h) * ratio; }
        else if (hx) h = Math.sign(h || 1) * Math.abs(w) / ratio; else w = Math.sign(w || 1) * Math.abs(h) * ratio;
        if (e.alt) { x0 = -w / 2; x1 = w / 2; y0 = -h / 2; y1 = h / 2; }
        else { if (hx < 0) x0 = x1 - w; else if (hx > 0) x1 = x0 + w; else { x0 = -w / 2; x1 = w / 2; } if (hy < 0) y0 = y1 - h; else if (hy > 0) y1 = y0 + h; else { y0 = -h / 2; y1 = h / 2; } }
      }
      const flipX = x1 < x0, flipY = y1 < y0; if (flipX) { const t = x0; x0 = x1; x1 = t; } if (flipY) { const t = y0; y0 = y1; y1 = t; }
      let nw = Math.max(x1 - x0, it.type === 'LINE' ? 0.01 : 1), nh = it.type === 'LINE' ? 0 : Math.max(y1 - y0, 1);
      const mx = (x0 + x1) / 2, my = (y0 + y1) / 2, ncx = cx + mx * cos - my * sin, ncy = cy + mx * sin + my * cos;
      let nx = ncx - nw / 2, ny = ncy - nh / 2;
      if (!it.rot) { const rx = Math.round(nx), ry = Math.round(ny); nw = Math.max(1, Math.round(nx + nw) - rx); if (it.type !== 'LINE') nh = Math.max(1, Math.round(ny + nh) - ry); nx = rx; ny = ry; } else { nx = r2(nx); ny = r2(ny); nw = r2(nw); nh = r2(nh); }
      d.gesture.apply(() => {
        if (!HD.store.has(it.id)) return; const p = {x: nx, y: ny, w: nw}; if (it.type !== 'LINE') p.h = nh;
        if (flipX) p.flipH = !it.flipH; else if (it.flipH !== !!prop(it.id, 'flipH')) p.flipH = it.flipH;
        if (flipY) p.flipV = !it.flipV; else if (it.flipV !== !!prop(it.id, 'flipV')) p.flipV = it.flipV;
        const fx = it.w ? nw / it.w : 1, fy = it.h ? nh / it.h : 1;
        if (it.type === 'VECTOR' && it.path) p.path = scalePath(it.path, fx, fy);
        if (it.type === 'TEXT') { if (hy) p.autoResize = 'none'; else if ((it.auto || 'wh') === 'wh') p.autoResize = 'h'; }
        HD.store.set(it.id, p); if (it.kids) scaleKids(it.kids, fx, fy);
      });
    }
  }
  /* several layers: scale their world boxes about the opposite side */
  function resizeMany(d, e, px, py) {
    const hx = d.h[0], hy = d.h[1], b = d.box; let ax = hx > 0 ? b.x : hx < 0 ? b.x + b.w : b.x + b.w / 2, ay = hy > 0 ? b.y : hy < 0 ? b.y + b.h : b.y + b.h / 2;
    if (e.alt) { ax = b.x + b.w / 2; ay = b.y + b.h / 2; }
    const sx0 = hx ? (hx > 0 ? b.x + b.w : b.x) : 0, sy0 = hy ? (hy > 0 ? b.y + b.h : b.y) : 0;
    let fx = hx && Math.abs(sx0 - ax) > 1e-6 ? (px - ax) / (sx0 - ax) : 1, fy = hy && Math.abs(sy0 - ay) > 1e-6 ? (py - ay) / (sy0 - ay) : 1;
    if (e.shift || !hx || !hy) { if (e.shift) { if (hx && hy) { const f = Math.max(Math.abs(fx), Math.abs(fy)); fx = f * Math.sign(fx || 1); fy = f * Math.sign(fy || 1); } else if (hx) fy = Math.abs(fx); else fx = Math.abs(fy); } }
    fx = Math.max(0.001, Math.abs(fx)); fy = Math.max(0.001, Math.abs(fy));
    d.gesture.apply(() => {
      for (const it of d.items) { if (!HD.store.has(it.id)) continue;
        const quarter = Math.abs(Math.round(it.rot / 90)) % 2 === 1, kx = quarter ? fy : fx, ky = quarter ? fx : fy;
        const ncx = ax + (it.cw[0] - ax) * fx, ncy = ay + (it.cw[1] - ay) * fy, c = HD.math.apply(it.pinv, ncx, ncy);
        const nw = Math.max(0.01, r2(it.w * kx)), nh = it.type === 'LINE' ? 0 : Math.max(0.01, r2(it.h * ky)), p = {x: r2(c[0] - nw / 2), y: r2(c[1] - nh / 2), w: nw};
        if (it.type !== 'LINE') p.h = nh; if (it.type === 'VECTOR' && it.path) p.path = scalePath(it.path, kx, ky);
        HD.store.set(it.id, p); if (it.kids) scaleKids(it.kids, kx, ky); }
    });
  }
  function worldAng(id) { const m = wm(id); return Math.atan2(m[1], m[0]) / DEG; }
  function startLine(e, hd) { const id = hd.box.single, it = snapshot(id), m = wm(id), A = HD.math.apply;
    const fixedW = hd.h[0] > 0 ? A(m, 0, 0) : A(m, it.w, 0);
    return {mode: 'line', id: id, it: it, end: hd.h[0], fixed: HD.math.apply(it.pinv, fixedW[0], fixedW[1]), gesture: new Gesture('Resize'), cands: snapCands([id], it.parent)}; }
  function doLine(d, e) {
    let px = e.x, py = e.y; state.guides = []; if (snapping(e) && !e.shift) { const s = snapPoint(px, py, d.cands); px = s[0]; py = s[1]; }
    const p = HD.math.apply(d.it.pinv, px, py); let a = d.end > 0 ? d.fixed : p, b = d.end > 0 ? p : d.fixed;
    let ang = Math.atan2(b[1] - a[1], b[0] - a[0]), len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (e.shift) { ang = Math.round(ang / (Math.PI / 4)) * (Math.PI / 4); if (d.end > 0) b = [a[0] + Math.cos(ang) * len, a[1] + Math.sin(ang) * len]; else a = [b[0] - Math.cos(ang) * len, b[1] - Math.sin(ang) * len]; }
    const cx = (a[0] + b[0]) / 2, cy = (a[1] + b[1]) / 2;
    d.gesture.apply(() => { if (HD.store.has(d.id)) HD.store.set(d.id, {x: r2(cx - len / 2), y: r2(cy), w: Math.max(0.01, r2(len)), rot: r2(ang / DEG)}); });
  }
  function startRotate(e, hd) {
    const ids = topLevel(selIds()).filter(id => !prop(id, 'locked')); if (!ids.length) return null; const b = union(ids);
    const pivot = ids.length === 1 ? centreW(ids[0]) : [b.x + b.w / 2, b.y + b.h / 2];
    return {mode: 'rotate', ids: ids, items: ids.map(snapshot), pivot: pivot, a0: Math.atan2(e.y - pivot[1], e.x - pivot[0]), gesture: new Gesture('Rotate'), delta: 0};
  }
  function doRotate(d, e) {
    let da = (Math.atan2(e.y - d.pivot[1], e.x - d.pivot[0]) - d.a0) / DEG;
    if (e.shift) { if (d.items.length === 1) { const t = Math.round((d.items[0].rot + da) / 15) * 15; da = t - d.items[0].rot; } else da = Math.round(da / 15) * 15; }
    d.delta = da; const cos = Math.cos(da * DEG), sin = Math.sin(da * DEG);
    d.gesture.apply(() => {
      for (const it of d.items) { if (!HD.store.has(it.id)) continue;
        const vx = it.cw[0] - d.pivot[0], vy = it.cw[1] - d.pivot[1], c = HD.math.apply(it.pinv, d.pivot[0] + vx * cos - vy * sin, d.pivot[1] + vx * sin + vy * cos);
        let rot = (it.rot + da) % 360; if (rot > 180) rot -= 360; if (rot <= -180) rot += 360;
        HD.store.set(it.id, {x: r2(c[0] - it.w / 2), y: r2(c[1] - it.h / 2), rot: r2(rot)}); }
    });
  }

  /* ---------------------------------------------------------------- tool: move / select */
  HD.tools.register('move', {
    cursor: 'default',
    down(e) {
      const hd = handleAt(e.sx, e.sy);
      if (hd) { state.drag = hd.kind === 'rotate' ? startRotate(e, hd) : hd.kind === 'line' ? startLine(e, hd) : startResize(e, hd); if (state.drag) return; }
      const deep = HD.render.hitTest(e.x, e.y, {deep: true}), t = resolveHit(deep, e);
      if (!t) { if (!e.shift) { HD.sel.clear(); state.scope = null; } state.drag = {mode: 'marquee', wx: e.x, wy: e.y, base: e.shift ? selIds() : []}; return; }
      let deferred = null;
      if (e.shift) { HD.sel.toggle(t); if (!HD.sel.has(t)) return; }
      else if (!HD.sel.has(t)) HD.sel.set([t]); else if (selIds().length > 1) deferred = t;
      state.hover = null;
      if (!canEdit()) return;
      state.drag = {mode: 'pending', sx: e.sx, sy: e.sy, e0: e, deferred: deferred};
    },
    move(e) {
      const d = state.drag;
      if (!d) {
        const hd = handleAt(e.sx, e.sy);
        if (hd) { setCursor(handleCursor(hd)); if (state.hover) { state.hover = null; redraw(); } return; }
        setCursor('default'); const t = resolveHit(HD.render.hitTest(e.x, e.y, {deep: true}), e), h = t && !HD.sel.has(t) ? t : null;
        if (h !== state.hover) { state.hover = h; redraw(); } return;
      }
      if (d.mode === 'pending') {
        if (Math.hypot(e.sx - d.sx, e.sy - d.sy) < 3) return;
        if (e.alt) { const copies = act.duplicate(true); if (!copies.length) { state.drag = null; return; } }
        const m = startMove(d.e0, selIds()); if (!m) { state.drag = null; return; } state.drag = m; m.moved = true; doMove(m, e); redraw(); return;
      }
      if (d.mode === 'move') { doMove(d, e); redraw(); return; }
      if (d.mode === 'resize') { doResize(d, e); redraw(); return; }
      if (d.mode === 'line') { doLine(d, e); redraw(); return; }
      if (d.mode === 'rotate') { doRotate(d, e); redraw(); return; }
      if (d.mode === 'marquee') {
        const r = {x: Math.min(d.wx, e.x), y: Math.min(d.wy, e.y), w: Math.abs(e.x - d.wx), h: Math.abs(e.y - d.wy)}; state.marquee = r;
        let hits = HD.render.nodesInRect(r, HD.sel.page) || [];
        const seen = new Set(d.base), out = d.base.slice();
        for (const id of hits) { const ch = chain(id); if (!ch.length || ch.some(c => prop(c, 'locked'))) continue;
          let pick = ch[0]; if (ch.length > 1 && DROP[typeOf(ch[0])] && !HD.math.rectContains(r, aabb(ch[0]))) pick = ch[1]; else if (DROP[typeOf(ch[0])] && ch.length === 1 && !HD.math.rectContains(r, aabb(ch[0])) && HD.store.children(ch[0]).length) continue;
          if (!seen.has(pick)) { seen.add(pick); out.push(pick); } }
        HD.sel.set(out); redraw();
      }
    },
    up(e) {
      const d = state.drag; state.drag = null; state.marquee = null; state.guides = []; state.gaps = []; state.dropInto = null;
      if (!d) return;
      if (d.gesture) d.gesture.end();
      if (d.mode === 'pending' && d.deferred && !e.shift) HD.sel.set([d.deferred]);
    },
    dbl(e) {
      const deep = HD.render.hitTest(e.x, e.y, {deep: true}); if (!deep) return; const ch = chain(deep); if (ch.some(c => prop(c, 'locked'))) return;
      const cur = selIds().length === 1 ? selIds()[0] : null; let i = cur ? ch.indexOf(cur) : -1, next = cur;
      if (i >= 0 && i < ch.length - 1) { next = ch[i + 1]; HD.sel.set([next]); state.scope = HD.store.parent(next); }
      if (next && typeOf(next) === 'TEXT' && next === deep && canEdit()) TextEdit.open(next);
    },
    key(ev) {
      const ids = selIds();
      if (ev.key === 'Escape') { if (state.drag) { cancelDrag(); redraw(); return true; } if (ids.length) { const p = HD.store.parent(ids[0]); if (p && !pageLike(p) && state.scope) { HD.sel.set([p]); state.scope = pageLike(HD.store.parent(p)) ? null : HD.store.parent(p); } else { HD.sel.clear(); state.scope = null; } return true; } return false; }
      if (ev.key === 'Enter' && ids.length) {
        if (ev.shiftKey) { const p = HD.store.parent(ids[0]); if (p && !pageLike(p)) HD.sel.set([p]); return true; }
        if (ids.length === 1 && typeOf(ids[0]) === 'TEXT' && canEdit()) { TextEdit.open(ids[0]); return true; }
        const kids = []; for (const id of ids) for (const k of HD.store.children(id)) kids.push(k); if (kids.length) { HD.sel.set(kids); state.scope = ids[0]; } return true;
      }
      if (ev.key === 'Tab' && ids.length) { const p = HD.store.parent(ids[0]), sib = HD.store.children(p), i = sib.indexOf(ids[0]); if (sib.length) HD.sel.set([sib[(i + (ev.shiftKey ? 1 : sib.length - 1)) % sib.length]]); return true; }
      if (/^Arrow/.test(ev.key) && ids.length && canEdit() && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        const k = ev.shiftKey ? 10 : 1, dx = ev.key === 'ArrowLeft' ? -k : ev.key === 'ArrowRight' ? k : 0, dy = ev.key === 'ArrowUp' ? -k : ev.key === 'ArrowDown' ? k : 0;
        act.nudge(dx, dy); return true;
      }
      return false;
    },
    leave() { state.hover = null; cancelDrag(); }
  });

  /* ---------------------------------------------------------------- tools: frame + shapes (drawn as a preview, created on release) */
  function shapeTool(type, label) {
    return {
      cursor: 'crosshair',
      down(e) { if (!canEdit()) return; let p = [e.x, e.y]; const parent = containerAt(e.x, e.y); const cands = snapCands([], parent); if (snapping(e)) p = snapPoint(p[0], p[1], cands);
        state.drag = {mode: 'draw', type: type, x0: p[0], y0: p[1], x1: p[0], y1: p[1], parent: parent, cands: cands, sx: e.sx, sy: e.sy, big: false}; },
      move(e) { const d = state.drag; if (!d || d.mode !== 'draw') { return; }
        let p = [e.x, e.y]; state.guides = []; if (snapping(e) && !(type === 'LINE' && e.shift)) p = snapPoint(p[0], p[1], d.cands);
        if (Math.hypot(e.sx - d.sx, e.sy - d.sy) > 3) d.big = true; d.x1 = p[0]; d.y1 = p[1]; d.shift = e.shift; d.alt = e.alt; state.draft = draftRect(d); redraw(); },
      up(e) { const d = state.drag; state.drag = null; state.draft = null; state.guides = []; if (!d || d.mode !== 'draw') return;
        d.shift = e.shift; d.alt = e.alt; const id = commitShape(d, label); if (id) { HD.sel.set([id]); HD.tools.set('move'); } },
      key(ev) { if (ev.key === 'Escape') { if (state.drag) { cancelDrag(); redraw(); } else HD.tools.set('move'); return true; } return false; },
      leave() { cancelDrag(); }
    };
  }
  function draftRect(d) {
    if (d.type === 'LINE') { let x1 = d.x1, y1 = d.y1; if (d.shift) { const a = Math.round(Math.atan2(y1 - d.y0, x1 - d.x0) / (Math.PI / 4)) * (Math.PI / 4), l = Math.hypot(x1 - d.x0, y1 - d.y0); x1 = d.x0 + Math.cos(a) * l; y1 = d.y0 + Math.sin(a) * l; }
      return {type: 'LINE', x0: d.x0, y0: d.y0, x1: x1, y1: y1}; }
    let w = d.x1 - d.x0, h = d.y1 - d.y0; if (d.shift) { const m = Math.max(Math.abs(w), Math.abs(h)); w = m * Math.sign(w || 1); h = m * Math.sign(h || 1); }
    let x = d.x0, y = d.y0; if (d.alt) { x = d.x0 - w; y = d.y0 - h; w *= 2; h *= 2; }
    if (w < 0) { x += w; w = -w; } if (h < 0) { y += h; h = -h; }
    return {type: d.type, x: x, y: y, w: w, h: h};
  }
  const SHAPE_PROPS = {
    FRAME: () => ({fills: [solid('#FFFFFF')], clip: true}), RECT: () => ({fills: [solid('#D9D9D9')]}), ELLIPSE: () => ({fills: [solid('#D9D9D9')]}),
    POLYGON: () => ({fills: [solid('#D9D9D9')], sides: 3}), STAR: () => ({fills: [solid('#D9D9D9')], sides: 5, ratio: 0.5}),
    LINE: () => ({strokes: [solid('#1A1A1F')], strokeWeight: 1}), SECTION: () => ({fills: [solid('#FFFFFF', 0.6)]})
  };
  function commitShape(d, label) {
    const inv = HD.math.inv(wm(d.parent)); let id = null;
    if (d.type === 'LINE') {
      const r = draftRect(d); let a = HD.math.apply(inv, r.x0, r.y0), b = HD.math.apply(inv, r.x1, r.y1); if (!d.big) b = [a[0] + 100, a[1]];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]), ang = Math.atan2(b[1] - a[1], b[0] - a[0]) / DEG, cx = (a[0] + b[0]) / 2, cy = (a[1] + b[1]) / 2;
      HD.store.tx('Draw line', () => { id = HD.store.create('LINE', d.parent, Object.assign({name: nextName('LINE'), x: r2(cx - len / 2), y: r2(cy), w: r2(len), h: 0, rot: r2(ang)}, SHAPE_PROPS.LINE())); });
      return id;
    }
    let r = draftRect(d); if (!d.big || r.w < 1 || r.h < 1) r = {x: d.x0, y: d.y0, w: 100, h: 100};
    const a = HD.math.apply(inv, r.x, r.y), b = HD.math.apply(inv, r.x + r.w, r.y + r.h);
    const x = Math.round(Math.min(a[0], b[0])), y = Math.round(Math.min(a[1], b[1])), w = Math.max(1, Math.round(Math.abs(b[0] - a[0]))), h = Math.max(1, Math.round(Math.abs(b[1] - a[1])));
    HD.store.tx(label, () => {
      id = HD.store.create(d.type, d.parent, Object.assign({name: nextName(d.type), x: x, y: y, w: w, h: h}, (SHAPE_PROPS[d.type] || SHAPE_PROPS.RECT)()));
      if (d.type === 'FRAME' && d.big) {   /* a frame drawn around loose layers adopts them */
        const box = {x: r.x, y: r.y, w: r.w, h: r.h}, sibs = HD.store.children(d.parent).filter(k => k !== id && !prop(k, 'locked') && HD.math.rectContains(box, aabb(k)));
        if (sibs.length) { const fm = HD.math.inv(HD.store.worldMatrix(id)); const moves = sibs.map(k => ({k: k, c: centreW(k), s: size(k)}));
          HD.store.move(sibs, id, null); for (const mv of moves) { const c = HD.math.apply(fm, mv.c[0], mv.c[1]); HD.store.set(mv.k, {x: r2(c[0] - mv.s[0] / 2), y: r2(c[1] - mv.s[1] / 2)}); } }
      }
    });
    return id;
  }
  HD.tools.register('frame', shapeTool('FRAME', 'Draw frame'));
  HD.tools.register('rect', shapeTool('RECT', 'Draw rectangle'));
  HD.tools.register('ellipse', shapeTool('ELLIPSE', 'Draw ellipse'));
  HD.tools.register('line', shapeTool('LINE', 'Draw line'));
  HD.tools.register('polygon', shapeTool('POLYGON', 'Draw polygon'));
  HD.tools.register('star', shapeTool('STAR', 'Draw star'));

  /* ---------------------------------------------------------------- tool: pen */
  HD.tools.register('pen', {
    cursor: 'crosshair',
    enter() { state.pen = {pts: [], cur: null, dragging: false}; },
    leave() { penFinish(false); state.pen = null; },
    down(e) {
      if (!canEdit()) return; const pn = state.pen; if (!pn) return;
      if (pn.pts.length >= 2) { const f = pn.pts[0], s = w2s(f.x, f.y); if (Math.hypot(s[0] - e.sx, s[1] - e.sy) <= 8) { penFinish(true); return; } }
      let x = e.x, y = e.y; if (e.shift && pn.pts.length) { const l = pn.pts[pn.pts.length - 1], a = Math.round(Math.atan2(y - l.y, x - l.x) / (Math.PI / 4)) * (Math.PI / 4), len = Math.hypot(x - l.x, y - l.y); x = l.x + Math.cos(a) * len; y = l.y + Math.sin(a) * len; }
      pn.pts.push({x: x, y: y}); pn.dragging = true; pn.dx = e.sx; pn.dy = e.sy;
    },
    move(e) { const pn = state.pen; if (!pn) return; pn.cur = {x: e.x, y: e.y};
      if (pn.dragging && state.down) { const p = pn.pts[pn.pts.length - 1]; if (Math.hypot(e.sx - pn.dx, e.sy - pn.dy) > 3) { p.o = {x: e.x, y: e.y}; p.i = {x: 2 * p.x - e.x, y: 2 * p.y - e.y}; } }
      redraw(); },
    up() { const pn = state.pen; if (pn) pn.dragging = false; },
    dbl() { const pn = state.pen; if (pn && pn.pts.length > 1) { pn.pts.pop(); penFinish(false); } },
    key(ev) { const pn = state.pen;
      if (ev.key === 'Enter' || ev.key === 'Escape') { if (pn && pn.pts.length) penFinish(false); else HD.tools.set('move'); return true; }
      if ((ev.key === 'Backspace' || ev.key === 'Delete') && pn && pn.pts.length) { pn.pts.pop(); redraw(); return true; }
      return false; }
  });
  function penFinish(closed) {
    const pn = state.pen; if (!pn) return; const pts = pn.pts; state.pen = {pts: [], cur: null, dragging: false};
    if (pts.length < 2 || !canEdit()) { redraw(); return; }
    const id = createVector(pts, closed); if (id) { HD.sel.set([id]); if (curName === 'pen') HD.tools.set('move'); } redraw();
  }

  /* ---------------------------------------------------------------- tool: pencil */
  HD.tools.register('pencil', {
    cursor: 'crosshair',
    down(e) { if (!canEdit()) return; state.drag = {mode: 'pencil', pts: [{x: e.x, y: e.y}]}; },
    move(e) { const d = state.drag; if (!d || d.mode !== 'pencil') return; const l = d.pts[d.pts.length - 1]; if (Math.hypot(e.x - l.x, e.y - l.y) * zoom() >= 1.5) { d.pts.push({x: e.x, y: e.y}); redraw(); } },
    up() { const d = state.drag; state.drag = null; if (!d || d.mode !== 'pencil' || d.pts.length < 2) return;
      const pts = smooth(simplify(d.pts, 1.6 / zoom())); const id = createVector(pts, false, {fills: []}); if (id) HD.sel.set([id]); },
    key(ev) { if (ev.key === 'Escape') { cancelDrag(); HD.tools.set('move'); return true; } return false; },
    leave() { cancelDrag(); }
  });

  /* ---------------------------------------------------------------- tool: text + the in-place editor */
  const TextEdit = {
    el: null, id: null, fresh: null, gesture: null,
    open(id) {
      if (!canEdit() || !HD.store.has(id)) return; this.commit(); this.id = id; this.fresh = null; this.make(String(prop(id, 'chars') || ''));
      this.gesture = new Gesture('Edit text'); this.hide = !!(HD.render.setEditing); if (this.hide) HD.render.setEditing(id);
      this.style(); this.place(); this.el.focus(); this.el.select();
    },
    openNew(wx, wy, fixedW) { if (!canEdit()) return; this.commit(); HD.sel.clear(); this.id = null; this.fresh = {x: wx, y: wy, w: fixedW || 0, parent: containerAt(wx, wy)}; this.make(''); this.hide = true; this.style(); this.place(); this.el.focus(); },
    make(text) {
      const ta = document.createElement('textarea'); ta.className = 'hd-textedit'; ta.value = text; ta.spellcheck = false; ta.setAttribute('aria-label', 'Text'); ta.setAttribute('autocapitalize', 'off'); ta.wrap = 'off';
      ta.addEventListener('input', () => this.input());
      ta.addEventListener('keydown', ev => { ev.stopPropagation(); if (ev.key === 'Escape' || (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey))) { ev.preventDefault(); this.commit(); } });
      ta.addEventListener('blur', () => { setTimeout(() => { if (this.el === ta) this.commit(); }, 0); });
      for (const t of ['pointerdown', 'dblclick', 'wheel', 'contextmenu', 'paste', 'copy', 'cut']) ta.addEventListener(t, ev => ev.stopPropagation());
      HD.tools.host.appendChild(ta); this.el = ta;
    },
    props() {
      if (this.id) { const id = this.id, fills = prop(id, 'fills') || []; let col = '#1A1A1F'; for (const f of fills) if (f && f.type === 'solid' && f.visible !== false) col = f.color;
        return {font: prop(id, 'font') || 'Inter', size: num(id, 'fontSize', 16), weight: num(id, 'fontWeight', 400), italic: !!prop(id, 'italic'), lh: prop(id, 'lineHeight'), ls: num(id, 'letterSpacing', 0),
          align: prop(id, 'align') || 'left', auto: prop(id, 'autoResize') || 'wh', w: num(id, 'w', 100), h: num(id, 'h', 20), color: col, tcase: prop(id, 'textCase') || 'none', alignV: prop(id, 'alignV') || 'top'}; }
      const d = HD.store.defaults('TEXT') || {};
      return {font: d.font || 'Inter', size: d.fontSize || 16, weight: d.fontWeight || 400, italic: false, lh: 'auto', ls: 0, align: 'left', auto: this.fresh.w ? 'h' : 'wh', w: this.fresh.w, h: 0, color: '#1A1A1F', tcase: 'none', alignV: 'top'};
    },
    style() {
      const ta = this.el, p = this.props(), st = ta.style; if (!ta) return;
      st.fontFamily = '"' + String(p.font).replace(/["\\]/g, '') + '", "Inter", "Noto Sans Devanagari", system-ui, sans-serif'; st.fontSize = p.size + 'px'; st.fontWeight = String(p.weight); st.fontStyle = p.italic ? 'italic' : 'normal';
      let lh = typeof p.lh === 'number' ? p.lh : 0;
      if (!lh && this.id && HD.layout && HD.layout.measureText) { try { const m = HD.layout.measureText(HD.store.get(this.id)); if (m && m.lineHeight) lh = m.lineHeight; else if (m && m.lines && m.lines.length && m.h) lh = m.h / m.lines.length; } catch (e) { /* fall back */ } }
      st.lineHeight = lh ? lh + 'px' : '1.2'; st.letterSpacing = p.ls + 'px'; st.textAlign = p.align === 'justify' ? 'left' : p.align;
      st.textTransform = p.tcase === 'upper' ? 'uppercase' : p.tcase === 'lower' ? 'lowercase' : p.tcase === 'title' ? 'capitalize' : 'none';
      st.color = this.hide ? p.color : 'transparent'; st.caretColor = p.color;
      const wrap = p.auto !== 'wh'; ta.wrap = wrap ? 'soft' : 'off'; st.whiteSpace = wrap ? 'pre-wrap' : 'pre';
      this.p = p; this.lhpx = lh || p.size * 1.2;
    },
    place() {
      const ta = this.el; if (!ta) return; const p = this.p || this.props(), st = ta.style;
      let m; if (this.id) { if (!HD.store.has(this.id)) { this.drop(); return; } const wmx = wm(this.id), A = HD.math.apply, o = A(wmx, 0, 0), ux = A(wmx, 1, 0), uy = A(wmx, 0, 1);
        const so = w2s(o[0], o[1]), sx = w2s(ux[0], ux[1]), sy = w2s(uy[0], uy[1]); m = [sx[0] - so[0], sx[1] - so[1], sy[0] - so[0], sy[1] - so[1], so[0], so[1]];
        p.w = num(this.id, 'w', 100); p.h = num(this.id, 'h', 20); }
      else { const s = w2s(this.fresh.x, this.fresh.y), z = zoom(); m = [z, 0, 0, z, s[0], s[1]]; }
      st.transform = 'matrix(' + m.map(v => r2(v * 1000) / 1000).join(',') + ')';
      if (p.auto === 'wh') { st.width = '4px'; st.width = Math.max(ta.scrollWidth + 4, this.id ? p.w : 4, 4) + 'px'; } else st.width = Math.max(4, p.w) + 'px';
      st.height = this.lhpx + 'px'; const sh = Math.max(ta.scrollHeight, this.lhpx); st.height = Math.max(sh, p.auto === 'none' ? p.h : 0) + 'px';
      let top = 0; if (this.id && p.auto === 'none' && p.alignV !== 'top') top = Math.max(0, (p.h - sh) * (p.alignV === 'middle' ? 0.5 : 1)); st.paddingTop = top + 'px';
      if (this.id && p.auto === 'wh' && p.align !== 'left') { const extra = parseFloat(st.width) - p.w; st.marginLeft = (p.align === 'center' ? -extra / 2 : -extra) + 'px'; } else st.marginLeft = '0';
    },
    input() { if (this.id && this.gesture) { const id = this.id, v = this.el.value; this.gesture.apply(() => { if (HD.store.has(id)) HD.store.set(id, {chars: v}); }); this.style(); } this.place(); },
    commit() {
      const ta = this.el; if (!ta) return; const v = ta.value, id = this.id, fr = this.fresh; this.drop();
      if (id) { if (this.gesture) this.gesture.end(); this.gesture = null;
        if (HD.store.has(id)) { if (!v.trim()) HD.store.tx('Delete empty text', () => HD.store.remove([id]));
          else { const n = HD.store.get(id), auto = !n.name || /^Text( \d+)?$/.test(n.name) || n.name === String(prop(id, 'chars')).slice(0, 40); if (auto) { const nm = v.replace(/\s+/g, ' ').trim().slice(0, 40); if (nm && nm !== n.name) HD.store.tx('Rename', () => HD.store.set(id, {name: nm})); } } }
        return; }
      if (fr && v.trim()) { const inv = HD.math.inv(wm(fr.parent)), a = HD.math.apply(inv, fr.x, fr.y); let nid = null;
        HD.store.tx('Add text', () => { const p = {name: v.replace(/\s+/g, ' ').trim().slice(0, 40), x: Math.round(a[0]), y: Math.round(a[1]), chars: v, fills: [solid('#1A1A1F')], autoResize: fr.w ? 'h' : 'wh'}; if (fr.w) p.w = Math.round(fr.w); nid = HD.store.create('TEXT', fr.parent, p); });
        if (nid) HD.sel.set([nid]); }
      if (curName === 'text') HD.tools.set('move');
    },
    drop() { const ta = this.el; this.el = null; this.id = null; this.fresh = null; this.p = null; if (this.hide && HD.render.setEditing) HD.render.setEditing(null); if (ta && ta.parentNode) ta.parentNode.removeChild(ta); redraw(); }
  };
  HD.tools.text = TextEdit;
  HD.tools.register('text', {
    cursor: 'text',
    down(e) { if (!canEdit()) return; const t = e.target; if (t && typeOf(t) === 'TEXT' && !prop(t, 'locked')) { state.drag = {mode: 'textedit', id: t}; return; } state.drag = {mode: 'textbox', x0: e.x, y0: e.y, sx: e.sx, sy: e.sy}; },
    move(e) { const d = state.drag; if (!d || d.mode !== 'textbox') return; if (Math.hypot(e.sx - d.sx, e.sy - d.sy) > 4) { state.draft = {type: 'TEXTBOX', x: Math.min(d.x0, e.x), y: Math.min(d.y0, e.y), w: Math.abs(e.x - d.x0), h: Math.abs(e.y - d.y0)}; redraw(); } },
    up(e) { const d = state.drag, dr = state.draft; state.drag = null; state.draft = null; if (!d) return;
      if (d.mode === 'textedit') { HD.sel.set([d.id]); TextEdit.open(d.id); return; }
      const ev = e.raw; if (ev && ev.preventDefault) ev.preventDefault();
      setTimeout(() => { if (dr && dr.w > 6) TextEdit.openNew(dr.x, dr.y, dr.w); else TextEdit.openNew(d.x0, d.y0, 0); }, 0); },
    key(ev) { if (ev.key === 'Escape') { HD.tools.set('move'); return true; } return false; },
    leave() { cancelDrag(); }
  });

  /* ---------------------------------------------------------------- tools: hand, zoom, comment */
  HD.tools.register('hand', {
    cursor: 'grab',
    down(e) { state.drag = {mode: 'hand', cx: e.raw.clientX, cy: e.raw.clientY}; setCursor('grabbing'); },
    move(e) { const d = state.drag; if (!d || d.mode !== 'hand') return; View.panBy(e.raw.clientX - d.cx, e.raw.clientY - d.cy); d.cx = e.raw.clientX; d.cy = e.raw.clientY; },
    up() { state.drag = null; setCursor('grab'); },
    key(ev) { if (ev.key === 'Escape' && !HD.tools.panOnly) { HD.tools.set('move'); return true; } return false; }
  });
  HD.tools.register('zoom', {
    cursor: 'zoom-in',
    down(e) { state.drag = {mode: 'zoom', wx: e.x, wy: e.y, sx: e.sx, sy: e.sy}; },
    move(e) { const d = state.drag; setCursor(e.alt ? 'zoom-out' : 'zoom-in'); if (!d || d.mode !== 'zoom') return; if (Math.hypot(e.sx - d.sx, e.sy - d.sy) > 4) { state.marquee = {x: Math.min(d.wx, e.x), y: Math.min(d.wy, e.y), w: Math.abs(e.x - d.wx), h: Math.abs(e.y - d.wy)}; redraw(); } },
    up(e) { const d = state.drag, m = state.marquee; state.drag = null; state.marquee = null; if (!d) return; if (m && m.w * zoom() > 8 && m.h * zoom() > 8) View.rect(m); else View.zoomAt(e.sx, e.sy, zoom() * (e.alt ? 0.5 : 2), true); },
    key(ev) { if (ev.key === 'Escape') { HD.tools.set('move'); return true; } return false; }
  });
  HD.tools.register('comment', {
    cursor: 'crosshair',
    down(e) { const t = HD.render.hitTest(e.x, e.y, {deep: true}); if (HD.ui && HD.ui.fire) HD.ui.fire('comment', {x: r2(e.x), y: r2(e.y), sx: e.sx, sy: e.sy, page: HD.sel.page, node: t || null}); },
    key(ev) { if (ev.key === 'Escape') { HD.tools.set('move'); return true; } return false; }
  });

  /* ---------------------------------------------------------------- overlay (screen space) */
  function poly(ctx, pts) { ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]); ctx.closePath(); }
  function outline(ctx, id, color, width) { if (!HD.store.has(id)) return; const c = corners(id).map(p => w2s(p[0], p[1])); ctx.strokeStyle = color; ctx.lineWidth = width;
    if (typeOf(id) === 'LINE') { ctx.beginPath(); ctx.moveTo(c[0][0], c[0][1]); ctx.lineTo(c[1][0], c[1][1]); ctx.stroke(); return; } poly(ctx, c); ctx.stroke(); }
  function badge(ctx, text, x, y, color) { ctx.font = '500 11px "Schibsted Grotesk", system-ui, sans-serif'; const w = Math.ceil(ctx.measureText(text).width) + 12; ctx.fillStyle = color;
    rrect(ctx, Math.round(x - w / 2), Math.round(y), w, 20, 5); ctx.fill(); ctx.fillStyle = '#fff'; ctx.textBaseline = 'middle'; ctx.textAlign = 'center'; ctx.fillText(text, Math.round(x), Math.round(y) + 10.5); ctx.textAlign = 'left'; }
  function rrect(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
  function fmt(v) { return String(Math.round(v * 100) / 100); }
  function shapePts(type, x, y, w, h, sides, ratio) {
    const cx = x + w / 2, cy = y + h / 2, out = [], n = Math.max(3, sides || (type === 'STAR' ? 5 : 3)), tot = type === 'STAR' ? n * 2 : n;
    for (let i = 0; i < tot; i++) { const a = -Math.PI / 2 + i * 2 * Math.PI / tot, k = type === 'STAR' && i % 2 ? (ratio || 0.5) : 1; out.push([cx + Math.cos(a) * w / 2 * k, cy + Math.sin(a) * h / 2 * k]); }
    return out;
  }
  function drawOverlay(ctx) {
    ctx.save(); ctx.lineJoin = 'round';
    const acc = ACCENT, ids = selIds(), editing = TextEdit.el && TextEdit.id;
    /* other people: their selections, then their cursors */
    const users = HD.net && HD.net.users, me = HD.net && HD.net.cid;
    if (users && users.forEach) users.forEach((u, cid) => { if (!u || cid === me || u.cid === me || u.page !== HD.sel.page) return; const col = u.color || '#EE8F35';
      for (const id of (u.sel || []).slice(0, 50)) outline(ctx, id, col, 1.5); });
    if (state.dropInto && HD.store.has(state.dropInto)) outline(ctx, state.dropInto, acc, 2);
    if (state.hover && HD.store.has(state.hover) && !state.drag) outline(ctx, state.hover, acc, 2);
    /* selection */
    if (ids.length && !(state.drag && state.drag.mode === 'marquee' && !ids.length)) {
      const quiet = state.drag && (state.drag.mode === 'move');
      if (ids.length > 1 && ids.length <= 300) for (const id of ids) outline(ctx, id, acc, 1);
      const box = selBox();
      if (box && !editing) {
        ctx.strokeStyle = acc; ctx.lineWidth = ids.length === 1 ? 1.5 : 1;
        if (box.line) { ctx.beginPath(); ctx.moveTo(box.pts[0][0], box.pts[0][1]); ctx.lineTo(box.pts[1][0], box.pts[1][1]); ctx.stroke(); } else { poly(ctx, box.pts); ctx.stroke(); }
        if (canEdit() && !quiet && curName === 'move') {
          const hs = box.line ? [[-1, 0], [1, 0]] : HANDLES.filter(h => h[0] && h[1]);
          for (const h of hs) { const p = handlePos(box, h); ctx.save(); ctx.translate(p[0], p[1]); ctx.rotate(box.ang); ctx.fillStyle = '#fff'; ctx.strokeStyle = acc; ctx.lineWidth = 1.5;
            if (box.line) { ctx.beginPath(); ctx.arc(0, 0, 4, 0, Math.PI * 2); ctx.fill(); ctx.stroke(); } else { ctx.fillRect(-3.5, -3.5, 7, 7); ctx.strokeRect(-3.5, -3.5, 7, 7); } ctx.restore(); }
        }
        /* size badge under the box (or the angle while rotating) */
        let label = '';
        if (state.drag && state.drag.mode === 'rotate') label = fmt(ids.length === 1 ? num(ids[0], 'rot') : state.drag.delta) + '\u00B0';
        else if (ids.length === 1) { const s = size(ids[0]); label = fmt(s[0]) + ' \u00D7 ' + fmt(s[1]); } else if (box.world) label = fmt(box.world.w) + ' \u00D7 ' + fmt(box.world.h);
        if (label && !quiet) { let lo = box.pts[0]; let cx = 0, cy = 0; for (const p of box.pts) { cx += p[0] / 4; cy += p[1] / 4; if (p[1] > lo[1]) lo = p; }
          const maxY = Math.max.apply(null, box.pts.map(p => p[1])); badge(ctx, label, cx, maxY + 8, acc); }
      }
      if (editing) outline(ctx, TextEdit.id, acc, 1);
    }
    /* marquee */
    if (state.marquee) { const m = state.marquee, a = w2s(m.x, m.y), b = w2s(m.x + m.w, m.y + m.h); ctx.fillStyle = 'rgba(110,85,240,.10)'; ctx.strokeStyle = acc; ctx.lineWidth = 1;
      ctx.fillRect(a[0], a[1], b[0] - a[0], b[1] - a[1]); ctx.strokeRect(Math.round(a[0]) + 0.5, Math.round(a[1]) + 0.5, Math.round(b[0] - a[0]), Math.round(b[1] - a[1])); }
    /* shape being drawn */
    const dr = state.draft;
    if (dr) { ctx.lineWidth = 1; ctx.strokeStyle = acc;
      if (dr.type === 'LINE') { const a = w2s(dr.x0, dr.y0), b = w2s(dr.x1, dr.y1); ctx.strokeStyle = '#1A1A1F'; ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); }
      else { const a = w2s(dr.x, dr.y), b = w2s(dr.x + dr.w, dr.y + dr.h), w = b[0] - a[0], h = b[1] - a[1]; ctx.fillStyle = dr.type === 'FRAME' ? 'rgba(255,255,255,.9)' : dr.type === 'TEXTBOX' ? 'rgba(110,85,240,.06)' : '#D9D9D9';
        if (dr.type === 'ELLIPSE') { ctx.beginPath(); ctx.ellipse(a[0] + w / 2, a[1] + h / 2, Math.abs(w / 2), Math.abs(h / 2), 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke(); }
        else if (dr.type === 'POLYGON' || dr.type === 'STAR') { poly(ctx, shapePts(dr.type, a[0], a[1], w, h)); ctx.fill(); ctx.stroke(); }
        else { ctx.fillRect(a[0], a[1], w, h); ctx.strokeRect(Math.round(a[0]) + 0.5, Math.round(a[1]) + 0.5, Math.round(w), Math.round(h)); }
        if (dr.type !== 'TEXTBOX') badge(ctx, fmt(Math.round(dr.w)) + ' \u00D7 ' + fmt(Math.round(dr.h)), a[0] + w / 2, b[1] + 8, acc); } }
    /* pencil stroke */
    if (state.drag && state.drag.mode === 'pencil') { const pts = state.drag.pts; ctx.strokeStyle = '#1A1A1F'; ctx.lineWidth = Math.max(1, 2 * zoom()); ctx.lineCap = 'round'; ctx.beginPath();
      pts.forEach((p, i) => { const s = w2s(p.x, p.y); if (i) ctx.lineTo(s[0], s[1]); else ctx.moveTo(s[0], s[1]); }); ctx.stroke(); }
    /* pen path */
    const pn = state.pen;
    if (pn && pn.pts.length) { const S = p => w2s(p.x, p.y); ctx.strokeStyle = acc; ctx.lineWidth = 1.5; ctx.beginPath(); const f = S(pn.pts[0]); ctx.moveTo(f[0], f[1]);
      const seg = (a, b) => { const sb = S(b); if (a.o || b.i) { const c1 = S(a.o || a), c2 = S(b.i || b); ctx.bezierCurveTo(c1[0], c1[1], c2[0], c2[1], sb[0], sb[1]); } else ctx.lineTo(sb[0], sb[1]); };
      for (let i = 1; i < pn.pts.length; i++) seg(pn.pts[i - 1], pn.pts[i]);
      if (pn.cur && !pn.dragging) seg(pn.pts[pn.pts.length - 1], pn.cur); ctx.stroke();
      const last = pn.pts[pn.pts.length - 1];
      if (last.o) { const a = S(last.i), b = S(last.o), c = S(last); ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); for (const q of [a, b]) { ctx.beginPath(); ctx.arc(q[0], q[1], 3, 0, Math.PI * 2); ctx.fillStyle = acc; ctx.fill(); } void c; }
      pn.pts.forEach((p, i) => { const s = S(p); ctx.fillStyle = '#fff'; ctx.strokeStyle = acc; ctx.lineWidth = 1.5; ctx.beginPath(); if (i === 0 && pn.pts.length > 1) ctx.arc(s[0], s[1], 5, 0, Math.PI * 2); else ctx.rect(s[0] - 3, s[1] - 3, 6, 6); ctx.fill(); ctx.stroke(); }); }
    /* smart guides + equal gaps */
    if (state.guides.length || state.gaps.length) { const gc = '#F0447C'; ctx.strokeStyle = gc; ctx.fillStyle = gc; ctx.lineWidth = 1;
      for (const g of state.guides) { ctx.beginPath(); if (g.x !== undefined) { const a = w2s(g.x, g.a), b = w2s(g.x, g.b), x = Math.round(a[0]) + 0.5; ctx.moveTo(x, a[1] - 6); ctx.lineTo(x, b[1] + 6); } else { const a = w2s(g.a, g.y), b = w2s(g.b, g.y), y = Math.round(a[1]) + 0.5; ctx.moveTo(a[0] - 6, y); ctx.lineTo(b[0] + 6, y); } ctx.stroke(); }
      for (const g of state.gaps) { const a = g.axis === 'x' ? w2s(g.s, g.at) : w2s(g.at, g.s), b = g.axis === 'x' ? w2s(g.e, g.at) : w2s(g.at, g.e); ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]);
        if (g.axis === 'x') { ctx.moveTo(a[0], a[1] - 4); ctx.lineTo(a[0], a[1] + 4); ctx.moveTo(b[0], b[1] - 4); ctx.lineTo(b[0], b[1] + 4); } else { ctx.moveTo(a[0] - 4, a[1]); ctx.lineTo(a[0] + 4, a[1]); ctx.moveTo(b[0] - 4, b[1]); ctx.lineTo(b[0] + 4, b[1]); } ctx.stroke();
        badge(ctx, fmt(Math.round(g.e - g.s)), (a[0] + b[0]) / 2 + (g.axis === 'y' ? 22 : 0), (a[1] + b[1]) / 2 + (g.axis === 'x' ? 6 : -10), gc); } }
    /* other people's cursors */
    if (users && users.forEach) users.forEach((u, cid) => { if (!u || cid === me || u.cid === me || u.page !== HD.sel.page || typeof u.x !== 'number') return; const s = w2s(u.x, u.y), col = u.color || '#EE8F35';
      ctx.save(); ctx.translate(s[0], s[1]); ctx.fillStyle = col; ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5; ctx.lineJoin = 'round'; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(0, 17); ctx.lineTo(4.8, 12.6); ctx.lineTo(12, 12.6); ctx.closePath(); ctx.stroke(); ctx.fill();
      const name = String(u.name || 'Guest').slice(0, 24); ctx.font = '500 12px "Schibsted Grotesk", system-ui, sans-serif'; const w = Math.ceil(ctx.measureText(name).width) + 14; rrect(ctx, 11, 17, w, 22, 6); ctx.fillStyle = col; ctx.fill(); ctx.fillStyle = '#fff'; ctx.textBaseline = 'middle'; ctx.fillText(name, 18, 28.5); ctx.restore(); });
    ctx.restore();
    if (TextEdit.el) TextEdit.place();
  }

  /* ---------------------------------------------------------------- actions (bound to keys / menus by the UI) */
  const CLIP_KEY = 'hoola.design.clip';
  function serialize(id) { const n = HD.store.get(id); if (!n) return null; const p = {}; for (const k in n) if (k !== 'parent' && k !== 'idx') p[k] = n[k];
    return {id: id, p: JSON.parse(JSON.stringify(p)), kids: HD.store.children(id).map(serialize).filter(Boolean)}; }
  function instantiate(tree, parent, before, map) { const p = Object.assign({}, tree.p), type = p.type; delete p.type; const id = HD.store.create(type, parent, p, before || undefined); map[tree.id] = id; for (const k of tree.kids) instantiate(k, id, null, map); return id; }
  function remap(map) { for (const old in map) { const id = map[old], n = HD.store.get(id); if (!n || !Array.isArray(n.reactions)) continue; let hit = false; const rs = n.reactions.map(r => { if (r && map[r.to]) { hit = true; return Object.assign({}, r, {to: map[r.to]}); } return r; }); if (hit) HD.store.set(id, {reactions: rs}); } }
  function nextSibling(id) { const sib = HD.store.children(HD.store.parent(id)), i = sib.indexOf(id); return i >= 0 && i + 1 < sib.length ? sib[i + 1] : null; }
  function worldMoveTo(id, cw) { const s = size(id), c = HD.math.apply(pinv(id), cw[0], cw[1]); HD.store.set(id, {x: r2(c[0] - s[0] / 2), y: r2(c[1] - s[1] / 2)}); }
  function shift(id, dx, dy) { const d = lin(pinv(id), dx, dy); HD.store.set(id, {x: r2(num(id, 'x') + d[0]), y: r2(num(id, 'y') + d[1])}); }
  function tops() { return topLevel(selIds()); }
  function guard() { if (!canEdit()) { if (HD.ui && HD.ui.toast) HD.ui.toast('This file is view only.'); return false; } return true; }
  const act = HD.tools.act = {
    clipText() { const ids = tops(); if (!ids.length) return ''; const data = {hd: 1, file: HD.app && HD.app.file && HD.app.file.id, page: HD.sel.page, parent: HD.store.parent(ids[0]), nodes: ids.map(id => { const t = serialize(id); if (t) t.cw = centreW(id); return t; }).filter(Boolean), box: union(ids), at: Date.now()};
      const texts = ids.filter(id => typeOf(id) === 'TEXT').map(id => String(prop(id, 'chars') || '')); data.sig = texts.length ? texts.join('\n') : ids.map(id => (HD.store.get(id) || {}).name || '').join('\n');
      try { localStorage.setItem(CLIP_KEY, JSON.stringify(data)); } catch (e) { act._clip = data; } act._clip = data; return data.sig; },
    clip() { let d = null; try { d = JSON.parse(localStorage.getItem(CLIP_KEY) || 'null'); } catch (e) { d = null; } return d || act._clip || null; },
    copy() { const sig = act.clipText(); if (sig && navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(sig).catch(() => {}); return !!sig; },
    cut() { if (!guard()) return; if (act.copy()) act.remove(); },
    paste(at) {
      if (!guard()) return []; const data = act.clip(); if (!data || !data.nodes || !data.nodes.length) return [];
      const sel = selIds(); let parent = HD.sel.page, before = null;
      if (sel.length === 1 && DROP[typeOf(sel[0])] && !data.nodes.some(n => n.id === sel[0])) parent = sel[0];
      else if (sel.length) { parent = HD.store.parent(sel[0]); before = nextSibling(topLevel(sel).pop()); }
      else if (data.parent && HD.store.has(data.parent) && HD.store.pageOf && HD.store.pageOf(data.parent) === HD.sel.page) parent = data.parent;
      const same = data.file === (HD.app && HD.app.file && HD.app.file.id) && data.page === HD.sel.page && data.parent === parent && !at; const out = [], map = {};
      HD.store.tx('Paste', () => {
        for (const t of data.nodes) out.push(instantiate(t, parent, before, map)); remap(map);
        if (!same && data.box && !(prop(parent, 'layout') && prop(parent, 'layout').mode && prop(parent, 'layout').mode !== 'none')) {
          let target = at; if (!target) { if (parent !== HD.sel.page) { const b = aabb(parent); target = [b.x + b.w / 2, b.y + b.h / 2]; } else { const c = View.centre(); target = HD.render.screenToWorld(c[0], c[1]); } }
          const dx = target[0] - (data.box.x + data.box.w / 2), dy = target[1] - (data.box.y + data.box.h / 2);
          const bx = data.box.x + data.box.w / 2, by = data.box.y + data.box.h / 2; void dx; void dy;
          data.nodes.forEach((t, i) => { const cw = t.cw || [bx, by]; worldMoveTo(out[i], [Math.round(target[0] + cw[0] - bx), Math.round(target[1] + cw[1] - by)]); });
        }
      });
      HD.sel.set(out); return out;
    },
    pasteText(text, at) { if (!guard() || !text) return; const c = at || HD.render.screenToWorld.apply(null, View.centre()), parent = containerAt(c[0], c[1]), a = HD.math.apply(HD.math.inv(wm(parent)), c[0], c[1]); let id = null;
      HD.store.tx('Paste text', () => { id = HD.store.create('TEXT', parent, {name: text.replace(/\s+/g, ' ').trim().slice(0, 40) || 'Text', x: Math.round(a[0]), y: Math.round(a[1]), chars: text.slice(0, 20000), fills: [solid('#1A1A1F')], autoResize: 'wh'}); }); if (id) HD.sel.set([id]); },
    pasteImage(hash, w, h, name, at) { if (!guard()) return; const c = at || HD.render.screenToWorld.apply(null, View.centre()), parent = containerAt(c[0], c[1]), a = HD.math.apply(HD.math.inv(wm(parent)), c[0], c[1]); let id = null;
      HD.store.tx('Paste image', () => { id = HD.store.create('RECT', parent, {name: name || 'Image', x: Math.round(a[0] - w / 2), y: Math.round(a[1] - h / 2), w: Math.round(w), h: Math.round(h), fills: [{type: 'image', hash: hash, mode: 'fill', opacity: 1, visible: true}]}); }); if (id) HD.sel.set([id]); return id; },
    duplicate(quiet) {
      if (!guard()) return []; const ids = tops(); if (!ids.length) return []; const out = [], map = {};
      HD.store.tx('Duplicate', () => { for (const id of ids) { const t = serialize(id); if (t) out.push(instantiate(t, HD.store.parent(id), nextSibling(id), map)); } remap(map); });
      HD.sel.set(out); void quiet; return out;
    },
    remove() { if (!guard()) return; const ids = tops(); if (!ids.length) return; HD.sel.clear(); HD.store.tx('Delete', () => HD.store.remove(ids)); },
    selectAll() { const sel = selIds(), par = sel.length ? HD.store.parent(sel[0]) : (state.scope && HD.store.has(state.scope) ? state.scope : HD.sel.page); HD.sel.set(HD.store.children(par).filter(k => !prop(k, 'locked') && prop(k, 'visible') !== false)); },
    selectNone() { HD.sel.clear(); state.scope = null; },
    selectInverse() { const sel = new Set(selIds()), par = sel.size ? HD.store.parent(selIds()[0]) : HD.sel.page; HD.sel.set(HD.store.children(par).filter(k => !sel.has(k) && !prop(k, 'locked'))); },
    nudge(dx, dy) { if (!guard()) return; const ids = tops(); if (!ids.length) return; HD.store.tx('Nudge', () => { for (const id of ids) if (!prop(id, 'locked')) shift(id, dx, dy); }); },
    wrap(type) {
      if (!guard()) return null; const ids = tops(); if (!ids.length) return null; const parent = HD.store.parent(ids[ids.length - 1]), before = nextSibling(ids[ids.length - 1]);
      const inv = HD.math.inv(wm(parent)); let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      const cs = ids.map(id => { const c = corners(id).map(p => HD.math.apply(inv, p[0], p[1])); for (const p of c) { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); } const cw = centreW(id), cl = HD.math.apply(inv, cw[0], cw[1]); return {id: id, c: cl, s: size(id)}; });
      let gid = null;
      HD.store.tx(type === 'GROUP' ? 'Group' : 'Frame selection', () => {
        const p = {name: nextName(type), x: r2(x0), y: r2(y0), w: r2(x1 - x0), h: r2(y1 - y0)}; if (type === 'FRAME') { p.fills = []; p.clip = false; }
        gid = HD.store.create(type, parent, p, before || undefined); HD.store.move(ids, gid, null);
        for (const c of cs) HD.store.set(c.id, {x: r2(c.c[0] - x0 - c.s[0] / 2), y: r2(c.c[1] - y0 - c.s[1] / 2)});
      });
      if (gid) HD.sel.set([gid]); return gid;
    },
    group() { return act.wrap('GROUP'); },
    frameSelection() { return act.wrap('FRAME'); },
    ungroup() {
      if (!guard()) return; const ids = tops().filter(id => HOLDS[typeOf(id)] && HD.store.children(id).length); if (!ids.length) return; const out = [];
      HD.store.tx('Ungroup', () => { for (const g of ids) { const parent = HD.store.parent(g), kids = HD.store.children(g), grot = num(g, 'rot'), info = kids.map(k => ({k: k, c: centreW(k), s: size(k), rot: num(k, 'rot')}));
        HD.store.move(kids, parent, g); const inv = HD.math.inv(wm(parent));
        for (const it of info) { const c = HD.math.apply(inv, it.c[0], it.c[1]), p = {x: r2(c[0] - it.s[0] / 2), y: r2(c[1] - it.s[1] / 2)}; if (grot) p.rot = r2(it.rot + grot); HD.store.set(it.k, p); out.push(it.k); }
        HD.store.remove([g]); } });
      HD.sel.set(out.filter(id => HD.store.has(id)));
    },
    order(how) {
      if (!guard()) return; const ids = tops(); if (!ids.length) return;
      HD.store.tx('Reorder', () => {
        const byPar = new Map(); for (const id of ids) { const p = HD.store.parent(id); if (!byPar.has(p)) byPar.set(p, []); byPar.get(p).push(id); }
        byPar.forEach((list, par) => { const set = new Set(list), sib = HD.store.children(par);
          if (how === 'front') HD.store.move(list, par, null);
          else if (how === 'back') { const first = sib.find(k => !set.has(k)); if (first) HD.store.move(list, par, first); }
          else if (how === 'forward') { const top = list[list.length - 1]; let i = sib.indexOf(top) + 1; while (i < sib.length && set.has(sib[i])) i++; if (i < sib.length) HD.store.move(list, par, i + 1 < sib.length ? sib[i + 1] : null); }
          else if (how === 'backward') { let i = sib.indexOf(list[0]) - 1; while (i >= 0 && set.has(sib[i])) i--; if (i >= 0) HD.store.move(list, par, sib[i]); } });
      });
    },
    toggle(name) { if (!guard()) return; const ids = selIds(); if (!ids.length) return; const def = name === 'visible', allOn = ids.every(id => { const v = prop(id, name); return (v === undefined ? def : !!v) === true; });
      HD.store.tx(name === 'visible' ? 'Show / hide' : 'Lock / unlock', () => { for (const id of ids) HD.store.set(id, {[name]: !allOn}); }); },
    align(how) {
      if (!guard()) return; const ids = tops(); if (!ids.length) return; let ref = union(ids);
      if (ids.length === 1) { const p = HD.store.parent(ids[0]); if (pageLike(p)) return; ref = aabb(p); }
      HD.store.tx('Align', () => { for (const id of ids) { if (prop(id, 'locked')) continue; const b = aabb(id); let dx = 0, dy = 0;
        if (how === 'left') dx = ref.x - b.x; else if (how === 'hcenter') dx = ref.x + ref.w / 2 - (b.x + b.w / 2); else if (how === 'right') dx = ref.x + ref.w - (b.x + b.w);
        else if (how === 'top') dy = ref.y - b.y; else if (how === 'vcenter') dy = ref.y + ref.h / 2 - (b.y + b.h / 2); else if (how === 'bottom') dy = ref.y + ref.h - (b.y + b.h);
        if (dx || dy) shift(id, dx, dy); } });
    },
    distribute(axis, gap) {
      if (!guard()) return; const ids = tops(); if (ids.length < 3 && gap === undefined) return; const X = axis === 'h';
      const items = ids.map(id => ({id: id, b: aabb(id)})).sort((a, b) => X ? a.b.x - b.b.x : a.b.y - b.b.y); if (items.length < 2) return;
      const first = items[0].b, last = items[items.length - 1].b, total = items.reduce((s, it) => s + (X ? it.b.w : it.b.h), 0);
      const span = X ? last.x + last.w - first.x : last.y + last.h - first.y, g = gap !== undefined ? gap : (span - total) / (items.length - 1);
      HD.store.tx('Distribute', () => { let pos = X ? first.x : first.y; for (const it of items) { const d = pos - (X ? it.b.x : it.b.y); if (Math.abs(d) > 0.001) shift(it.id, X ? d : 0, X ? 0 : d); pos += (X ? it.b.w : it.b.h) + g; } });
    },
    tidy() {
      if (!guard()) return; const ids = tops(); if (ids.length < 2) return; const items = ids.map(id => ({id: id, b: aabb(id)})), u = union(ids), X = u.w >= u.h;
      items.sort((a, b) => X ? a.b.x - b.b.x : a.b.y - b.b.y); const total = items.reduce((s, it) => s + (X ? it.b.w : it.b.h), 0);
      const g = Math.max(0, Math.round(((X ? u.w : u.h) - total) / (items.length - 1)));
      HD.store.tx('Tidy up', () => { let pos = X ? u.x : u.y; for (const it of items) { const dm = pos - (X ? it.b.x : it.b.y), dc = (X ? u.y - it.b.y : u.x - it.b.x); shift(it.id, X ? dm : dc, X ? dc : dm); pos += (X ? it.b.w : it.b.h) + g; } });
    },
    flip(axis) {
      if (!guard()) return; const ids = tops(); if (!ids.length) return; const u = union(ids), name = axis === 'h' ? 'flipH' : 'flipV', info = ids.map(id => ({id: id, c: centreW(id), rot: num(id, 'rot')}));
      HD.store.tx('Flip', () => { for (const it of info) { const c = axis === 'h' ? [2 * (u.x + u.w / 2) - it.c[0], it.c[1]] : [it.c[0], 2 * (u.y + u.h / 2) - it.c[1]]; if (ids.length > 1) worldMoveTo(it.id, c);
        const p = {[name]: !prop(it.id, name)}; if (it.rot) p.rot = -it.rot; HD.store.set(it.id, p); } });
    },
    addFrame(w, h, name) {
      if (!guard()) return null; const kids = HD.store.children(HD.sel.page); let x = 0, y = 0;
      if (kids.length) { const u = union(kids); x = Math.round(u.x + u.w + 100); y = Math.round(u.y); }
      let id = null; HD.store.tx('Add frame', () => { id = HD.store.create('FRAME', HD.sel.page, {name: name || nextName('FRAME'), x: x, y: y, w: w, h: h, fills: [solid('#FFFFFF')], clip: true}); });
      if (id) { HD.sel.set([id]); View.fit(kids.length ? [id] : undefined); HD.tools.set('move'); } return id;
    },
    /* set a layer's size from the panel: vectors rescale their path, groups rescale their children, text boxes stop hugging */
    resizeTo(id, w, h) {
      const it = snapshot(id), p = {}; if (w !== undefined && w !== null) p.w = Math.max(it.type === 'LINE' ? 0.01 : 0.01, r2(w)); if (h !== undefined && h !== null && it.type !== 'LINE') p.h = Math.max(0.01, r2(h));
      const fx = p.w !== undefined && it.w ? p.w / it.w : 1, fy = p.h !== undefined && it.h ? p.h / it.h : 1;
      if (it.type === 'VECTOR' && it.path) p.path = scalePath(it.path, fx, fy);
      if (it.type === 'TEXT') { if (p.h !== undefined) p.autoResize = 'none'; else if ((it.auto || 'wh') === 'wh') p.autoResize = 'h'; }
      HD.store.set(id, p); if (it.kids) scaleKids(it.kids, fx, fy);
    },
    /* move layers to another parent / place in the stack and keep them where they are on the canvas */
    reparent(ids, parent, before) {
      if (!guard()) return false; ids = topLevel(alive(ids)); if (!ids.length || !HD.store.has(parent)) return false;
      for (const id of ids) if (id === parent || isInside(parent, id) || id === before) return false;
      const lay = prop(parent, 'layout'), auto = !!(lay && lay.mode && lay.mode !== 'none'), info = ids.map(id => ({id: id, from: HD.store.parent(id), c: centreW(id), s: size(id)}));
      HD.store.tx('Reorder layers', () => { HD.store.move(ids, parent, before || null); if (auto) return; const inv = HD.math.inv(wm(parent));
        for (const it of info) { if (it.from === parent) continue; const c = HD.math.apply(inv, it.c[0], it.c[1]); HD.store.set(it.id, {x: r2(c[0] - it.s[0] / 2), y: r2(c[1] - it.s[1] / 2)}); } });
      return true;
    },
    rename(id, name) { if (!guard() || !HD.store.has(id)) return; name = String(name).slice(0, 200); if (name && name !== (HD.store.get(id) || {}).name) HD.store.tx('Rename', () => HD.store.set(id, {name: name})); },
    zoomSelection() { const ids = selIds(); if (ids.length) View.fit(ids); },
    undo() { if (canEdit() && HD.store.canUndo()) { TextEdit.commit(); HD.store.undo(); HD.sel.set(selIds()); } },
    redo() { if (canEdit() && HD.store.canRedo()) { HD.store.redo(); HD.sel.set(selIds()); } }
  };
})();

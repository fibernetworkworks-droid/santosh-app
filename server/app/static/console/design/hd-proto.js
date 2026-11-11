/* HOOLA DESIGN - D6 prototype (docs/HOOLA_DESIGN_PLAN.md section 2 "prototype", phase D6): the Prototype tab, the wiring
   on the canvas and the player. Plain browser JS, no dependencies, no eval. Loaded after hd-ui.js, before hd-app.js.

   WHAT IS WRITTEN INTO THE DOCUMENT (every edit = one HD.store.tx = one undo step; the player writes nothing):
     any node   reactions: [{trigger: 'click'|'hover'|'press'|'drag'|'after'|'key', delay (ms, after), key (KeyboardEvent.key, key),
                             action: 'navigate'|'overlay'|'swap'|'close'|'back'|'scroll'|'url', to: '<node id>', url: 'https://...',
                             anim: {type: 'instant'|'dissolve'|'smart'|'move'|'moveout'|'push'|'slide'|'slideout',
                                    dir: 'left'|'right'|'up'|'down', dur: ms, ease: 'linear'|'in'|'out'|'inout'|'spring'}}]
     screen     protoStart: true + flowName   scroll: 'none'|'v'|'h'|'both'
                overlay: {pos: 'center'|'tl'|'tc'|'tr'|'bl'|'bc'|'br'|'manual', x, y, closeOutside, dim, dimColor, dimOpacity}
                (how THIS frame shows when a reaction opens it as an overlay)
     child of a screen   fixed: true  (stays put while the screen scrolls; drawn above the scrolling layers)
     page       device: 'none'|'phone'|'android'|'tablet'|'desktop'   deviceBg: '#RRGGBB' (the player's background)
   A "screen" = a FRAME / COMPONENT that lies on the page (or in sections on the page).

   HD.proto   open(frameId|null)  close()  isOpen  state()  link(frameId)  screens(page)  flows(page)
              clock.freeze() / clock.step(ms) / clock.release()   (a test steps the player's time by hand)
              pointOf(nodeId) -> [clientX, clientY]   wires() -> the arrows drawn on the canvas   handle() -> the + handle

   THE RENDERER. Every pixel of a frame is painted by HD.render.drawNode on the player's own canvas. Scrolling content,
   fixed layers and SMART ANIMATE need a frame drawn with other values than the document holds (a taller box, a layer
   half way between two places). hd-render.js has no override hook, but it reads the document late (S = () => HD.store),
   so for the length of ONE synchronous drawNode call HD.store is swapped for a read-only view: the real store plus a few
   scratch nodes under ids that start with '~'. Nothing is written, the real store never sees the scratch nodes, and a
   scratch id is never used twice with other values (the renderer caches extents per id). */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const ui = HD.ui;
  if (!ui || !HD.store || !HD.render) return;
  const h = ui.h, icon = ui.icon, clear = ui.clear;
  const ACC = '#6E55F0', EMPTY = Object.freeze([]);
  const SCREEN = {FRAME: 1, COMPONENT: 1};
  const CONT = {FRAME: 1, GROUP: 1, SECTION: 1, COMPONENT: 1, COMPONENT_SET: 1};
  const enc = encodeURIComponent;
  const TRIGGERS = [['click', 'On click'], ['hover', 'While hovering'], ['press', 'While pressing'], ['drag', 'On drag'], ['after', 'After a delay'], ['key', 'On a key press']];
  const ACTIONS = [['navigate', 'Navigate to'], ['overlay', 'Open overlay'], ['swap', 'Swap overlay'], ['close', 'Close overlay'], ['back', 'Back'], ['scroll', 'Scroll to'], ['url', 'Open link']];
  const ANIMS = [['instant', 'Instant'], ['dissolve', 'Dissolve'], ['smart', 'Smart animate'], ['move', 'Move in'], ['moveout', 'Move out'], ['push', 'Push'], ['slide', 'Slide in'], ['slideout', 'Slide out']];
  const EASES = [['linear', 'Linear'], ['in', 'Ease in'], ['out', 'Ease out'], ['inout', 'Ease in and out'], ['spring', 'Spring']];
  const SCROLLS = [['none', 'No scrolling'], ['v', 'Vertical'], ['h', 'Horizontal'], ['both', 'Both directions']];
  const DEVICE_LIST = [['none', 'No device'], ['phone', 'Phone'], ['android', 'Android phone'], ['tablet', 'Tablet'], ['desktop', 'Desktop']];
  const OVERLAY_POS = [['center', 'Centre'], ['tl', 'Top left'], ['tc', 'Top centre'], ['tr', 'Top right'], ['bl', 'Bottom left'], ['bc', 'Bottom centre'], ['br', 'Bottom right'], ['manual', 'Manual']];
  /* own simple outlines: screen size in px, corner radius, bezel, a stand under the desktop */
  const DEVICES = {
    phone: {w: 390, h: 844, r: 46, bez: 14, turn: true}, android: {w: 412, h: 915, r: 30, bez: 12, turn: true},
    tablet: {w: 820, h: 1180, r: 30, bez: 20, turn: true}, desktop: {w: 1440, h: 900, r: 12, bez: 16, stand: 110}
  };
  const DIRV = {left: [-1, 0], right: [1, 0], up: [0, -1], down: [0, 1]};
  const OPP = {left: 'right', right: 'left', up: 'down', down: 'up'};
  const NEEDS_TO = {navigate: 1, overlay: 1, swap: 1, scroll: 1};
  const HAS_ANIM = {navigate: 1, overlay: 1, swap: 1, close: 1, back: 1, scroll: 1};
  const DIRECTED = {move: 1, moveout: 1, push: 1, slide: 1, slideout: 1};

  /* ================================================================ the document, read */
  const st = () => HD.store;
  function N(id) { return id ? st().get(id) : undefined; }
  function P(id, name) { return st().prop(id, name); }
  function num(v, d) { return typeof v === 'number' && isFinite(v) ? v : d; }
  function nv(id, name, d) { return num(P(id, name), d === undefined ? 0 : d); }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function canEdit() { const u = HD.tools && HD.tools.u; return !!(u && u.canEdit ? u.canEdit() : !st().readOnly); }
  function typing(ev) { const t = ev.target; return !!(t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)); }
  function label(list, v) { const o = list.find(x => x[0] === v); return o ? o[1] : String(v || ''); }
  function nameOf(id) { const n = N(id); return n ? (n.name || n.type) : ''; }

  function isScreen(id) {
    const n = N(id); if (!n || !SCREEN[n.type]) return false;
    let p = n.parent, g = 0;
    while (p && g++ < 50) { const pn = N(p); if (!pn) return false; if (pn.type === 'PAGE') return true; if (pn.type !== 'SECTION') return false; p = pn.parent; }
    return false;
  }
  function screenOf(id) { let c = id, g = 0; while (c && g++ < 500) { const n = N(c); if (!n || n.type === 'PAGE' || n.type === 'DOCUMENT') return null; if (isScreen(c)) return c; c = n.parent; } return null; }
  /* the screens of a page in reading order (rows top to bottom, each row left to right) */
  function screens(page) {
    const out = [];
    if (!page || !N(page)) return out;
    (function walk(pid, d) { for (const k of st().children(pid)) { const n = N(k); if (!n || n.visible === false) continue; if (SCREEN[n.type]) out.push(k); else if (n.type === 'SECTION' && d < 6) walk(k, d + 1); } })(page, 0);
    const b = new Map(out.map(id => [id, st().worldBounds(id)]));
    out.sort((p, q) => (b.get(p).y - b.get(q).y) || (b.get(p).x - b.get(q).x));
    const rows = [];
    for (const id of out) { const r = b.get(id), row = rows[rows.length - 1]; if (row && r.y < row.y + row.h * 0.5) row.ids.push(id); else rows.push({y: r.y, h: r.h, ids: [id]}); }
    const res = [];
    for (const row of rows) { row.ids.sort((p, q) => b.get(p).x - b.get(q).x); for (const id of row.ids) res.push(id); }
    return res;
  }
  function flows(page) { return screens(page).filter(id => P(id, 'protoStart') === true).map(id => ({id: id, name: String(P(id, 'flowName') || nameOf(id))})); }
  function reactions(id) { const n = N(id), r = n && n.reactions; return Array.isArray(r) ? r : EMPTY; }
  /* one reaction with every default filled in */
  function rx(r) {
    r = r && typeof r === 'object' ? r : {};
    const a = r.anim && typeof r.anim === 'object' ? r.anim : {};
    const trig = TRIGGERS.some(t => t[0] === r.trigger) ? r.trigger : 'click', act = ACTIONS.some(t => t[0] === r.action) ? r.action : 'navigate';
    return {trigger: trig, action: act, to: typeof r.to === 'string' ? r.to : null, url: typeof r.url === 'string' ? r.url : '', delay: Math.max(0, num(r.delay, 800)), key: typeof r.key === 'string' ? r.key : '',
      anim: {type: ANIMS.some(t => t[0] === a.type) ? a.type : 'instant', dir: DIRV[a.dir] ? a.dir : 'left', dur: clamp(num(a.dur, 300), 0, 10000), ease: EASES.some(t => t[0] === a.ease) ? a.ease : 'out'}};
  }
  function overlayConf(id) {
    const o = P(id, 'overlay'), c = o && typeof o === 'object' ? o : {};
    return {pos: OVERLAY_POS.some(p => p[0] === c.pos) ? c.pos : 'center', x: num(c.x, 0), y: num(c.y, 0), closeOutside: c.closeOutside !== false, dim: c.dim !== false,
      dimColor: typeof c.dimColor === 'string' ? c.dimColor : '#000000', dimOpacity: clamp(num(c.dimOpacity, 0.4), 0, 1)};
  }
  function safeLink(url) { try { const u = new URL(String(url || '').trim()); return u.protocol === 'https:' && u.hostname ? u.href : null; } catch (e) { return null; } }
  function keyLabel(k) { return k === ' ' ? 'Space' : k.length === 1 ? k.toUpperCase() : k.replace(/^Arrow/, 'Arrow '); }

  /* ================================================================ the document, written (the editor only) */
  function write(lbl, fn, g) { if (!canEdit()) return; if (g && g.apply) g.apply(fn); else st().tx(lbl, fn); }
  function setProps(id, props, lbl, g) { write(lbl, () => { if (st().has(id)) st().set(id, props); }, g); }
  function writeReactions(id, list, lbl) { setProps(id, {reactions: list.length ? list : null}, lbl); }
  function cloneR(r) { return JSON.parse(JSON.stringify(r)); }
  function addReaction(id, r) { const list = reactions(id).map(cloneR); list.push(r); writeReactions(id, list, 'Add interaction'); return reactions(id).length === list.length ? list.length - 1 : -1; }
  function removeReaction(id, i) { const list = reactions(id).map(cloneR); if (i < 0 || i >= list.length) return; list.splice(i, 1); writeReactions(id, list, 'Remove interaction'); }
  function patchReaction(id, i, fn, lbl) { const list = reactions(id).map(cloneR); if (!list[i]) return; fn(list[i]); writeReactions(id, list, lbl || 'Change interaction'); }
  function defaultTarget(id) { const sc = screenOf(id), page = st().pageOf(id), all = screens(page); if (!all.length) return null; const i = all.indexOf(sc); const nx = all[i + 1] || all.find(s => s !== sc); return nx && nx !== sc ? nx : null; }
  function nextFlowName(page) { const used = new Set(flows(page).map(f => f.name)); for (let i = 1; i < 500; i++) if (!used.has('Flow ' + i)) return 'Flow ' + i; return 'Flow'; }

  /* ================================================================ a read-only view of the store with scratch nodes */
  const scratch = {keep: new Map(), keepKids: new Map(), temp: new Map(), tempKids: new Map(), seq: 0, made: 0};
  let view = null;
  function storeView() {
    const real = HD.store;
    if (view && view.__real === real) return view;
    view = Object.create(real); view.__real = real;
    const node = id => (id.charCodeAt(0) === 126 ? (scratch.temp.get(id) || scratch.keep.get(id)) : undefined);
    view.get = id => (typeof id === 'string' && node(id)) || real.get(id);
    view.has = id => (typeof id === 'string' && !!node(id)) || real.has(id);
    view.children = id => (typeof id === 'string' && id.charCodeAt(0) === 126 ? (scratch.tempKids.get(id) || scratch.keepKids.get(id) || EMPTY) : real.children(id));
    view.parent = id => { const n = view.get(id); return n ? n.parent : undefined; };
    view.prop = (id, name) => { const n = typeof id === 'string' ? node(id) : undefined; if (!n) return real.prop(id, name); const v = n[name]; return v !== undefined ? v : (real.defaults(n.type) || {})[name]; };
    view.readOnly = true;
    return view;
  }
  function withView(fn) { const real = HD.store; HD.store = storeView(); try { return fn(); } finally { HD.store = real; } }
  function sid() { scratch.made++; return '~' + (++scratch.seq); }
  function put(map, kidMap, n, kids) { const id = sid(); map.set(id, n); kidMap.set(id, kids || EMPTY); return id; }
  function drawId(ctx, id) { if (id.charCodeAt(0) !== 126) { HD.render.drawNode(ctx, id); return; } withView(() => HD.render.drawNode(ctx, id)); }

  /* ================================================================ a surface: one frame as the player shows it */
  let docVer = 1;
  function kidsExtent(fid) {
    let mx = 0, my = 0;
    for (const k of st().children(fid)) {
      const n = N(k); if (!n || n.visible === false) continue;
      const m = st().localMatrix(k), w = num(n.w, 100), hh = n.type === 'LINE' ? 0 : num(n.h, 100);
      for (const c of [[0, 0], [w, 0], [w, hh], [0, hh]]) { const x = m[0] * c[0] + m[2] * c[1] + m[4], y = m[1] * c[0] + m[3] * c[1] + m[5]; if (x > mx) mx = x; if (y > my) my = y; }
    }
    return [mx, my];
  }
  /* vw x vh = the window onto the frame (frame units); the content may be bigger: then it scrolls */
  function makeSurface(fid, vw, vh) {
    const n = N(fid); if (!n) return null;
    const fw = Math.max(1, num(n.w, 100)), fh = Math.max(1, num(n.h, 100)), sc = P(fid, 'scroll') || 'none', allowH = sc === 'h' || sc === 'both', allowV = sc === 'v' || sc === 'both';
    const ext = allowH || allowV ? kidsExtent(fid) : [0, 0];
    const cw = allowH ? Math.max(fw, Math.ceil(ext[0])) : fw, ch = allowV ? Math.max(fh, Math.ceil(ext[1])) : fh;
    vw = Math.min(vw === undefined ? fw : vw, cw); vh = Math.min(vh === undefined ? fh : vh, ch);
    const kids = st().children(fid), fixed = kids.filter(k => { const kn = N(k); return kn && kn.fixed === true && kn.visible !== false; });
    const s = {id: fid, vw: vw, vh: vh, cw: cw, ch: ch, sx: 0, sy: 0, maxX: Math.max(0, cw - vw), maxY: Math.max(0, ch - vh), root: fid, fixedRoot: null, fixed: new Set(fixed), own: [], ver: docVer};
    const scrolls = s.maxX > 0.5 || s.maxY > 0.5;
    if (cw !== fw || ch !== fh || (fixed.length && scrolls)) {
      const copy = Object.assign({}, n, {x: 0, y: 0, rot: 0, flipH: false, flipV: false, w: cw, h: ch}); delete copy.parent;
      s.root = put(scratch.keep, scratch.keepKids, copy, fixed.length && scrolls ? kids.filter(k => !s.fixed.has(k)) : kids); s.own.push(s.root);
      if (fixed.length && scrolls) { s.fixedRoot = put(scratch.keep, scratch.keepKids, {type: 'GROUP', name: 'Fixed', x: 0, y: 0, w: cw, h: ch}, fixed); s.own.push(s.fixedRoot); }
    }
    if (!scrolls) s.fixed = new Set();
    return s;
  }
  function dropSurface(s) { if (!s) return; for (const id of s.own) { scratch.keep.delete(id); scratch.keepKids.delete(id); } s.own = []; }
  function setScroll(s, x, y) { const ox = s.sx, oy = s.sy; s.sx = clamp(x, 0, s.maxX); s.sy = clamp(y, 0, s.maxY); return s.sx !== ox || s.sy !== oy; }
  /* ctx: frame units, origin at the surface's top-left */
  function drawSurface(ctx, s) {
    if (!s || !N(s.id)) return;
    ctx.save(); ctx.beginPath(); ctx.rect(0, 0, s.vw, s.vh); ctx.clip();
    ctx.save(); ctx.translate(-s.sx, -s.sy); drawId(ctx, s.root); ctx.restore();
    if (s.fixedRoot) drawId(ctx, s.fixedRoot);
    ctx.restore();
  }
  /* where a node of the surface is: {x, y, w, h} in frame units of the window (scroll taken off), or null */
  function rectIn(s, id) {
    if (!s || !N(id)) return null;
    if (id === s.id) return {x: 0, y: 0, w: s.vw, h: s.vh};
    if (!st().isAncestor(s.id, id)) return null;
    const inv = HD.math.inv(st().worldMatrix(s.id)), m = HD.math.mul(inv, st().worldMatrix(id)), n = N(id), w = num(n.w, 100), hh = n.type === 'LINE' ? 0 : num(n.h, 100);
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const c of [[0, 0], [w, 0], [w, hh], [0, hh]]) { const p = HD.math.apply(m, c[0], c[1]); x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); }
    let top = id, g = 0; while (g++ < 500) { const pn = N(top); if (!pn || pn.parent === s.id) break; top = pn.parent; }
    const fix = s.fixed.has(top);
    return {x: x0 - (fix ? 0 : s.sx), y: y0 - (fix ? 0 : s.sy), w: x1 - x0, h: y1 - y0};
  }
  /* every node under the point (frame units of the window), topmost first, children before their parent */
  function hitList(s, fx, fy) {
    const out = [];
    const collect = (id, x, y, kx, ky) => {
      const n = N(id); if (!n || n.visible === false) return;
      const m = HD.math.inv(st().localMatrix(id)), p = HD.math.apply(m, x, y), w = num(n.w, 100), hh = n.type === 'LINE' ? 0 : num(n.h, 100);
      const lx = p[0] * (kx || 1), ly = p[1] * (ky || 1), inside = lx >= 0 && ly >= 0 && lx <= w && ly <= hh;
      if (CONT[n.type]) { const clip = n.type !== 'GROUP' && n.type !== 'SECTION' && P(id, 'clip') !== false; if (inside || !clip) { const ks = st().children(id); for (let i = ks.length - 1; i >= 0; i--) collect(ks[i], lx, ly); } }
      else if (n.type === 'INSTANCE' && inside && n.comp && N(n.comp)) { const cw = nv(n.comp, 'w', 100), chh = nv(n.comp, 'h', 100), ks = st().children(n.comp); for (let i = ks.length - 1; i >= 0; i--) collect(ks[i], lx * (w ? cw / w : 1), ly * (hh ? chh / hh : 1)); }
      if (inside) out.push(id);
    };
    const kids = st().children(s.id);
    for (let i = kids.length - 1; i >= 0; i--) if (s.fixed.has(kids[i])) collect(kids[i], fx, fy);
    for (let i = kids.length - 1; i >= 0; i--) if (!s.fixed.has(kids[i])) collect(kids[i], fx + s.sx, fy + s.sy);
    if (fx >= 0 && fy >= 0 && fx <= s.vw && fy <= s.vh) out.push(s.id);
    return out;
  }
  /* the first node (topmost, then up its ancestors) that answers one of the triggers */
  function findReaction(s, cands, trigs) {
    for (const c of cands) {
      let id = c, g = 0;
      while (id && g++ < 500) {
        const n = N(id); if (!n || n.type === 'PAGE' || n.type === 'DOCUMENT') break;
        const list = reactions(id);
        for (let i = 0; i < list.length; i++) { const t = rx(list[i]).trigger; if (trigs.indexOf(t) >= 0) return {node: id, i: i, r: list[i]}; }
        if (id === s.id) break;
        id = n.parent;
      }
    }
    return null;
  }
  const scans = new Map();
  /* what a frame holds: its timed reactions, its key reactions, its hotspots */
  function scan(fid) {
    const c = scans.get(fid); if (c && c.ver === docVer) return c;
    const r = {ver: docVer, after: [], keys: [], hot: []}; let count = 0;
    st().walk(fid, (id, n) => { if (++count > 20000 || !n || n.visible === false) return false; const list = reactions(id); let hot = false;
      for (let i = 0; i < list.length; i++) { const t = rx(list[i]).trigger; if (t === 'after') r.after.push({node: id, i: i}); else if (t === 'key') r.keys.push({node: id, i: i}); else hot = true; }
      if (hot) r.hot.push(id); return true; });
    if (scans.size > 200) scans.clear();
    scans.set(fid, r); return r;
  }

  /* ================================================================ easing, colours */
  function bez(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    return t => { let x = t; for (let i = 0; i < 6; i++) { const f = ((ax * x + bx) * x + cx) * x - t, d = (3 * ax * x + 2 * bx) * x + cx; if (Math.abs(f) < 1e-5 || !d) break; x -= f / d; } x = clamp(x, 0, 1); return ((ay * x + by) * x + cy) * x; };
  }
  const EASE = {linear: t => t, in: bez(0.42, 0, 1, 1), out: bez(0, 0, 0.58, 1), inout: bez(0.42, 0, 0.58, 1), spring: t => 1 - Math.exp(-6.5 * t) * Math.cos(9 * t)};
  function ease(name, t) { if (t <= 0) return 0; if (t >= 1) return 1; return (EASE[name] || EASE.out)(t); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function hex3(c) { let x = String(c || '#000000').replace('#', ''); if (x.length === 3 || x.length === 4) x = x.split('').map(ch => ch + ch).join(''); const v = parseInt(x.slice(0, 6), 16); return isFinite(v) ? [(v >> 16) & 255, (v >> 8) & 255, v & 255] : [0, 0, 0]; }
  function mixHex(a, b, t) { const p = hex3(a), q = hex3(b); return '#' + [0, 1, 2].map(i => ('0' + Math.round(clamp(lerp(p[i], q[i], t), 0, 255)).toString(16)).slice(-2)).join('').toUpperCase(); }
  function rgba(hex, a) { const c = hex3(hex); return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')'; }
  function reduced() { try { return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); } catch (e) { return false; } }

  /* ================================================================ smart animate: the plan (once) and one frame of it */
  const NOT_LOOK = new Set(['x', 'y', 'w', 'h', 'rot', 'opacity', 'radius', 'fontSize', 'strokeWeight', 'parent', 'idx', 'name', 'reactions', 'fixed', 'protoStart', 'flowName', 'scroll', 'overlay',
    'cons', 'exports', 'locked', 'sizeH', 'sizeV', 'layoutPos', 'desc', 'minW', 'maxW', 'minH', 'maxH', 'layout', 'grids']);
  const LERPS = ['x', 'y', 'w', 'h', 'rot', 'opacity', 'fontSize', 'strokeWeight'];
  function sameJSON(a, b) { return a === b || JSON.stringify(a) === JSON.stringify(b); }
  function solids(a, b) { return Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.length > 0 && a.every((p, i) => p && b[i] && (p.type || 'solid') === 'solid' && (b[i].type || 'solid') === 'solid' && (p.visible !== false) === (b[i].visible !== false)); }
  function mixPaints(pa, pb, t) { return pb.map((p, i) => Object.assign({}, p, {color: mixHex(pa[i].color, p.color, t), opacity: lerp(num(pa[i].opacity, 1), num(p.opacity, 1), t)})); }
  function arr4(r) { return Array.isArray(r) ? [0, 1, 2, 3].map(i => num(+r[i], 0)) : [num(r, 0), num(r, 0), num(r, 0), num(r, 0)]; }
  function mixRadius(ra, rb, t) { if (!Array.isArray(ra) && !Array.isArray(rb)) return lerp(num(ra, 0), num(rb, 0), t); const A = arr4(ra), B = arr4(rb); return A.map((v, i) => lerp(v, B[i], t)); }
  function matchKids(aKids, bKids, depth) {
    const byKey = new Map(), key = n => n.type + '\n' + (n.name || '');
    for (const id of aKids) { const n = N(id); if (!n) continue; const k = key(n); if (!byKey.has(k)) byKey.set(k, []); byKey.get(k).push(id); }
    const pair = new Map(), taken = new Set();
    for (const b of bKids) { const n = N(b); if (!n) continue; const l = byKey.get(key(n)); if (l && l.length) { const a = l.shift(); pair.set(b, a); taken.add(a); } }
    const out = [], done = new Set(), at = new Map(aKids.map((id, i) => [id, i]));
    for (const b of bKids) {
      if (!N(b)) continue;
      const a = pair.get(b);
      if (a === undefined) { out.push({kind: 'in', id: b}); continue; }
      for (let i = 0; i < at.get(a); i++) { const x = aKids[i]; if (!taken.has(x) && !done.has(x) && N(x)) { done.add(x); out.push({kind: 'out', id: x}); } }
      out.push({kind: 'pair', plan: planPair(a, b, depth + 1)});
    }
    for (const x of aKids) if (!taken.has(x) && !done.has(x) && N(x)) out.push({kind: 'out', id: x});
    return out;
  }
  function planPair(aId, bId, depth) {
    const a = N(aId), b = N(bId), pl = {a: aId, b: bId, kids: null, look: true, fills: false, strokes: false, geo: false, changed: false};
    for (const k of new Set(Object.keys(a).concat(Object.keys(b)))) {
      if (NOT_LOOK.has(k)) continue;
      if (k === 'fills' || k === 'strokes') { if (sameJSON(a[k], b[k])) continue; if (solids(a[k], b[k])) pl[k] = true; else pl.look = false; continue; }
      if (!sameJSON(a[k], b[k])) pl.look = false;
    }
    for (const k of LERPS) if (Math.abs(nv(aId, k, k === 'opacity' ? 1 : 0) - nv(bId, k, k === 'opacity' ? 1 : 0)) > 0.001) pl.geo = true;
    if (!sameJSON(a.radius, b.radius)) pl.geo = true;
    if (CONT[a.type] && CONT[b.type] && depth < 12) pl.kids = matchKids(st().children(aId), st().children(bId), depth);
    pl.changed = pl.geo || !pl.look || pl.fills || pl.strokes || !!(pl.kids && pl.kids.some(k => k.kind !== 'pair' || k.plan.changed));
    return pl;
  }
  /* from = {id, sx, sy, fixed:Set}: the frame on screen (its scroll); to = the surface being opened */
  function smartPlan(from, to) {
    const order = s => { const ks = st().children(s.id); return ks.filter(k => !s.fixed.has(k)).concat(ks.filter(k => s.fixed.has(k))); };
    const a = N(from.id), b = N(to.id), kids = matchKids(order(from), order(to), 0);
    for (const k of kids) { const aid = k.kind === 'pair' ? k.plan.a : k.kind === 'out' ? k.id : null; k.off = aid && !from.fixed.has(aid) && (from.sx || from.sy) ? {x: -from.sx, y: -from.sy} : null; }
    return {from: from.id, to: to.id, kids: kids, fills: !!(a && b && !sameJSON(a.fills, b.fills) && solids(a.fills, b.fills))};
  }
  function fadeInto(id, alpha, parent, kids, off) {
    const n = N(id); if (!n || alpha <= 0.002) return;
    if (alpha >= 0.999 && !off) { kids.push(id); return; }
    const c = Object.assign({}, n, {opacity: nv(id, 'opacity', 1) * alpha, parent: parent});
    if (off) { c.x = num(n.x, 0) + off.x; c.y = num(n.y, 0) + off.y; }
    kids.push(put(scratch.temp, scratch.tempKids, c, st().children(id)));
  }
  function pairInto(pl, t, parent, kids, off, probe) {
    const a = N(pl.a), b = N(pl.b);
    if (!b) return;
    if (!a || (!pl.changed && !off)) { kids.push(pl.b); return; }
    const ox = off ? off.x : 0, oy = off ? off.y : 0;
    const g = {x: lerp(nv(pl.a, 'x') + ox, nv(pl.b, 'x'), t), y: lerp(nv(pl.a, 'y') + oy, nv(pl.b, 'y'), t), w: lerp(nv(pl.a, 'w', 100), nv(pl.b, 'w', 100), t), h: lerp(nv(pl.a, 'h', 100), nv(pl.b, 'h', 100), t), rot: lerp(nv(pl.a, 'rot'), nv(pl.b, 'rot'), t), parent: parent};
    if (b.type === 'LINE') delete g.h;
    const op = lerp(nv(pl.a, 'opacity', 1), nv(pl.b, 'opacity', 1), t);
    if (probe) probe.push({a: pl.a, b: pl.b, name: b.name || '', x: g.x, y: g.y, w: g.w, h: g.h, rot: g.rot, opacity: op});
    if (!pl.look && !pl.kids) {       /* a leaf whose content is not the same: both, cross-faded, on the moving box */
      if (t < 0.998) kids.push(put(scratch.temp, scratch.tempKids, Object.assign({}, a, g, {opacity: nv(pl.a, 'opacity', 1) * (1 - t)}), st().children(pl.a)));
      if (t > 0.002) kids.push(put(scratch.temp, scratch.tempKids, Object.assign({}, b, g, {opacity: nv(pl.b, 'opacity', 1) * t}), st().children(pl.b)));
      return;
    }
    const c = Object.assign({}, b, g, {opacity: op});
    if (a.radius !== undefined || b.radius !== undefined) c.radius = mixRadius(a.radius, b.radius, t);
    if (pl.fills) c.fills = mixPaints(a.fills, b.fills, t);
    if (pl.strokes) c.strokes = mixPaints(a.strokes, b.strokes, t);
    if (a.fontSize !== undefined || b.fontSize !== undefined) c.fontSize = lerp(nv(pl.a, 'fontSize', 16), nv(pl.b, 'fontSize', 16), t);
    if (a.strokeWeight !== undefined || b.strokeWeight !== undefined) c.strokeWeight = lerp(nv(pl.a, 'strokeWeight', 1), nv(pl.b, 'strokeWeight', 1), t);
    let mine = null;
    if (pl.kids) { mine = []; const id = sid(); for (const k of pl.kids) kidInto(k, t, id, mine, null, probe); scratch.temp.set(id, c); scratch.tempKids.set(id, mine); kids.push(id); return; }
    kids.push(put(scratch.temp, scratch.tempKids, c, st().children(pl.b)));
  }
  function kidInto(k, t, parent, kids, off, probe) {
    if (k.kind === 'pair') pairInto(k.plan, t, parent, kids, off, probe);
    else if (k.kind === 'in') fadeInto(k.id, t, parent, kids, null);
    else fadeInto(k.id, 1 - t, parent, kids, off);
  }
  /* the scratch frame for time t (0..1): the id to draw, or null */
  function smartFrame(plan, t, surf, probe) {
    scratch.temp.clear(); scratch.tempKids.clear();
    const a = N(plan.from), b = N(plan.to); if (!b) return null;
    const root = Object.assign({}, b, {x: 0, y: 0, rot: 0, flipH: false, flipV: false, w: surf.cw, h: surf.ch}); delete root.parent;
    if (plan.fills && a) root.fills = mixPaints(a.fills, b.fills, t);
    const id = sid(), kids = [];
    for (const k of plan.kids) kidInto(k, t, id, kids, k.off, probe);
    scratch.temp.set(id, root); scratch.tempKids.set(id, kids);
    return id;
  }

  /* ================================================================ the player */
  const Pl = {open: false, el: null, canvas: null, ctx: null, stage: null, dpr: 1, W: 0, H: 0, page: null, start: null, base: null, overlays: [], history: [], zoom: 'fit', L: null, anim: null,
    timers: [], timerT: 0, hints: null, hover: null, press: null, down: null, raf: 0, stale: false, pushed: false, mom: null, glide: null, ro: null, bar: {}, ask: null, probe: [], offs: [], cursor: ''};
  let vclock = null;
  function now() { return vclock !== null ? vclock : performance.now(); }
  function wake() { if (!Pl.open || vclock !== null || Pl.raf) return; Pl.raf = requestAnimationFrame(() => { Pl.raf = 0; frame(); }); }

  function cssVar(name, def) { try { const v = getComputedStyle(Pl.el || document.documentElement).getPropertyValue(name).trim(); return v || def; } catch (e) { return def; } }
  function layoutFor(fid) {
    const n = N(fid) || {}, page = st().pageOf(fid), devKey = (page && P(page, 'device')) || 'none', dev = DEVICES[devKey] || null;
    const W = Pl.W, H = Pl.H, fw = Math.max(1, num(n.w, 100)), fh = Math.max(1, num(n.h, 100));
    let dw = fw, dh = fh, f = 1, bz = 0, stand = 0;
    if (dev) { const turn = dev.turn && fw > fh; dw = turn ? dev.h : dev.w; dh = turn ? dev.w : dev.h; f = dw / fw; bz = dev.bez; stand = dev.stand || 0; }
    const pad = W < 520 ? 12 : 28, availW = Math.max(40, W - pad * 2), availH = Math.max(40, H - pad * 2), totW = dw + bz * 2, totH = dh + bz * 2 + stand;
    const kd = Pl.zoom === 'fill' ? availW / totW : Pl.zoom === '100' ? 1 : Math.min(1, availW / totW, availH / totH);
    let sw = dw * kd, sh = dh * kd;
    if (!dev) { sw = Math.min(sw, availW); sh = Math.min(sh, availH); }       /* no device: the window itself is the limit, the rest scrolls */
    const bodyW = sw + bz * 2 * kd, bodyH = sh + bz * 2 * kd, allH = bodyH + stand * kd;
    const ox = Math.round((W - bodyW) / 2), oy = allH <= availH + 0.5 ? Math.round((H - allH) / 2) : pad;
    const pbg = page ? P(page, 'deviceBg') : null;
    return {dev: dev, devKey: devKey, kd: kd, k: kd * f, x: ox + bz * kd, y: oy + bz * kd, w: sw, h: sh, vw: sw / (kd * f), vh: sh / (kd * f), bez: bz * kd, r: dev ? Math.max(0, dev.r - dev.bez) * kd : 0,
      bodyX: ox, bodyY: oy, bodyW: bodyW, bodyH: bodyH, bodyR: dev ? dev.r * kd : 0, stand: stand * kd, bg: typeof pbg === 'string' && /^#[0-9a-f]{3,8}$/i.test(pbg) ? pbg : cssVar('--stage', '#17161F')};
  }
  function rr(c, x, y, w, hh, r) {
    r = Math.max(0, Math.min(r, w / 2, hh / 2)); c.beginPath();
    if (r < 0.5) { c.rect(x, y, w, hh); return; }
    c.moveTo(x + r, y); c.lineTo(x + w - r, y); c.arcTo(x + w, y, x + w, y + r, r); c.lineTo(x + w, y + hh - r); c.arcTo(x + w, y + hh, x + w - r, y + hh, r);
    c.lineTo(x + r, y + hh); c.arcTo(x, y + hh, x, y + hh - r, r); c.lineTo(x, y + r); c.arcTo(x, y, x + r, y, r); c.closePath();
  }
  function drawDevice(c, L) {
    if (!L.dev) return;
    const x = L.bodyX, y = L.bodyY, w = L.bodyW, hh = L.bodyH, kd = L.kd;
    if (L.stand) {                                      /* a neck and a foot under the desktop */
      const nw = w * 0.13, nx = x + (w - nw) / 2, fy = y + hh + L.stand;
      c.fillStyle = '#2A2933'; c.beginPath(); c.moveTo(nx, y + hh - 2); c.lineTo(nx + nw, y + hh - 2); c.lineTo(nx + nw + 14 * kd, fy - 12 * kd); c.lineTo(nx - 14 * kd, fy - 12 * kd); c.closePath(); c.fill();
      rr(c, x + w * 0.32, fy - 14 * kd, w * 0.36, 14 * kd, 7 * kd); c.fillStyle = '#34333F'; c.fill();
    }
    rr(c, x, y, w, hh, L.bodyR); c.fillStyle = '#1C1B23'; c.fill(); c.lineWidth = Math.max(1, 1.5 * kd); c.strokeStyle = '#4A4858'; c.stroke();
    rr(c, L.x, L.y, L.w, L.h, L.r); c.fillStyle = '#000000'; c.fill();
    c.fillStyle = '#3B3A47';
    const land = L.w > L.h && L.dev.turn, b = L.bez;
    if (L.devKey === 'phone') { const pw = Math.min(L.w, L.h) * 0.16, ph = Math.max(2, b * 0.3); if (land) rr(c, x + (b - ph) / 2, y + (hh - pw) / 2, ph, pw, ph / 2); else rr(c, x + (w - pw) / 2, y + (b - ph) / 2, pw, ph, ph / 2); c.fill(); }
    else if (L.devKey !== 'desktop') { const r = Math.max(1.5, b * 0.2); c.beginPath(); if (land) c.arc(x + b / 2, y + hh / 2, r, 0, Math.PI * 2); else c.arc(x + w / 2, y + b / 2, r, 0, Math.PI * 2); c.fill(); }
  }
  function placeOverlay(ov) {
    const L = Pl.L, c = ov.conf, s = ov.surf, fw = L.vw, fh = L.vh;
    let x = (fw - s.vw) / 2, y = (fh - s.vh) / 2;
    if (c.pos === 'manual') { x = c.x; y = c.y; }
    else if (c.pos !== 'center') { if (c.pos[0] === 't') y = 0; else if (c.pos[0] === 'b') y = fh - s.vh; if (c.pos[1] === 'l') x = 0; else if (c.pos[1] === 'r') x = fw - s.vw; }
    ov.x = x; ov.y = y;
  }
  function drawDim(c, ov, alpha) { if (!ov.conf.dim || alpha <= 0) return; c.fillStyle = rgba(ov.conf.dimColor, ov.conf.dimOpacity * alpha); c.fillRect(0, 0, Pl.L.vw, Pl.L.vh); }
  /* c: CSS px, origin at the screen's top-left. upTo = how many overlays to draw (default all) */
  function drawState(c, upTo) {
    const L = Pl.L; c.save(); c.scale(L.k, L.k);
    drawSurface(c, Pl.base);
    const n = upTo === undefined ? Pl.overlays.length : upTo;
    for (let i = 0; i < n; i++) { const ov = Pl.overlays[i]; drawDim(c, ov, 1); c.save(); c.translate(ov.x, ov.y); drawSurface(c, ov.surf); c.restore(); }
    c.restore();
  }
  function bitmap(w, hh, fn) {
    const d = Pl.dpr, cv = document.createElement('canvas'); cv.width = Math.max(1, Math.round(w * d)); cv.height = Math.max(1, Math.round(hh * d));
    const c = cv.getContext('2d'); c.setTransform(d, 0, 0, d, 0, 0); fn(c); return cv;
  }
  function snapState(upTo) { const L = Pl.L; return {cv: bitmap(L.w, L.h, c => drawState(c, upTo)), x: L.x, y: L.y, w: L.w, h: L.h}; }
  function snapOverlay(ov) { const L = Pl.L, s = ov.surf; return {cv: bitmap(s.vw * L.k, s.vh * L.k, c => { c.scale(L.k, L.k); drawSurface(c, s); }), w: s.vw * L.k, h: s.vh * L.k}; }

  /* ---------------------------------------------------------------- painting one frame of the player */
  function animType(a) { let t = a ? a.type : 'instant'; if (t !== 'instant' && t !== 'dissolve' && reduced()) t = 'dissolve'; if (t !== 'instant' && (!a.dur || a.dur < 1)) t = 'instant'; return t; }
  function drawAnim(c, a, e) {
    const L = Pl.L;
    if (a.kind === 'smart') { Pl.probe = []; const id = smartFrame(a.plan, e, Pl.base, Pl.probe); if (id) { c.save(); c.scale(L.k, L.k); c.beginPath(); c.rect(0, 0, Pl.base.vw, Pl.base.vh); c.clip(); drawId(c, id); c.restore(); } scratch.temp.clear(); scratch.tempKids.clear(); return; }
    if (a.kind === 'screen') {
      const A = a.A, B = a.B, v = DIRV[a.dir] || DIRV.left, W = Math.max(A.w, B.w), H = Math.max(A.h, B.h);
      let ax = 0, ay = 0, bx = 0, by = 0, aa = 1, ba = 1, bFirst = false;
      if (a.type === 'dissolve') ba = e;
      else if (a.type === 'move') { bx = -v[0] * (1 - e) * W; by = -v[1] * (1 - e) * H; }
      else if (a.type === 'moveout') { ax = v[0] * e * W; ay = v[1] * e * H; bFirst = true; }
      else if (a.type === 'push') { ax = v[0] * e * W; ay = v[1] * e * H; bx = ax - v[0] * W; by = ay - v[1] * H; }
      else if (a.type === 'slide') { bx = -v[0] * (1 - e) * W; by = -v[1] * (1 - e) * H; ax = v[0] * e * W * 0.3; ay = v[1] * e * H * 0.3; aa = 1 - 0.25 * e; }
      else if (a.type === 'slideout') { ax = v[0] * e * W; ay = v[1] * e * H; bx = -v[0] * (1 - e) * W * 0.3; by = -v[1] * (1 - e) * H * 0.3; ba = 0.75 + 0.25 * e; bFirst = true; }
      const dA = () => { c.globalAlpha = aa; c.drawImage(A.cv, A.x - L.x + ax, A.y - L.y + ay, A.w, A.h); }, dB = () => { c.globalAlpha = ba; c.drawImage(B.cv, bx, by, B.w, B.h); };
      if (bFirst) { dB(); dA(); } else { dA(); dB(); }
      c.globalAlpha = 1; return;
    }
    /* an overlay coming (ovin) or going (ovout) over what lies under it */
    const p = a.kind === 'ovin' ? e : 1 - e, v = DIRV[a.dir] || DIRV.up, ov = a.ov;
    c.drawImage(a.under.cv, 0, 0, a.under.w, a.under.h);
    c.save(); c.scale(L.k, L.k); drawDim(c, ov.ref, p); c.restore();
    let x = ov.x * L.k, y = ov.y * L.k, al = 1;
    if (a.type === 'dissolve' || a.type === 'smart') al = p;
    else if (a.out) { x += v[0] * (1 - p) * L.w; y += v[1] * (1 - p) * L.h; }
    else { x -= v[0] * (1 - p) * L.w; y -= v[1] * (1 - p) * L.h; }
    c.globalAlpha = al; c.drawImage(ov.bmp.cv, x, y, ov.bmp.w, ov.bmp.h); c.globalAlpha = 1;
  }
  function clipRect() { const L = Pl.L, a = Pl.anim; if (a && a.kind === 'screen' && !L.dev) { const x0 = Math.min(a.A.x, L.x), y0 = Math.min(a.A.y, L.y), x1 = Math.max(a.A.x + a.A.w, L.x + L.w), y1 = Math.max(a.A.y + a.A.h, L.y + L.h); return [x0, y0, x1 - x0, y1 - y0]; } return [L.x, L.y, L.w, L.h]; }
  function paint(t) {
    const c = Pl.ctx, d = Pl.dpr, L = Pl.L; if (!c || !L) return;
    c.setTransform(d, 0, 0, d, 0, 0); c.globalAlpha = 1; c.globalCompositeOperation = 'source-over';
    c.fillStyle = L.bg; c.fillRect(0, 0, Pl.W, Pl.H);
    drawDevice(c, L);
    const cr = clipRect();
    c.save(); rr(c, cr[0], cr[1], cr[2], cr[3], L.r); c.clip(); c.translate(L.x, L.y);
    const a = Pl.anim;
    if (a) { const p = a.dur > 0 ? clamp((t - a.t0) / a.dur, 0, 1) : 1; a.p = p; try { drawAnim(c, a, ease(a.ease, p)); } catch (err) { if (window.console) console.error('[HD.proto]', err); a.p = 1; } if (a.p >= 1) { endAnim(); Pl.settle = true; } }
    else { try { drawState(c); } catch (err) { if (window.console) console.error('[HD.proto]', err); } }
    if (Pl.hints) { const p = (t - Pl.hints.t0) / 700; if (p >= 1) Pl.hints = null; else { const al = p < 0.15 ? p / 0.15 : 1 - (p - 0.15) / 0.85; for (const r of Pl.hints.rects) { rr(c, r.x, r.y, r.w, r.h, 3); c.fillStyle = 'rgba(110,85,240,' + (0.22 * al) + ')'; c.fill(); c.lineWidth = 1.5; c.strokeStyle = 'rgba(110,85,240,' + (0.9 * al) + ')'; c.stroke(); } } }
    c.restore();
    if (scratch.made > 30000 && !Pl.anim) flushScratch();
  }
  function flushScratch() { scratch.made = 0; try { if (HD.render.clearCaches) HD.render.clearCaches(); } catch (e) { /* the renderer owns its caches */ } }
  function endAnim() { const a = Pl.anim; Pl.anim = null; if (!a) return; if (a.after) { try { a.after(); } catch (e) { /* nothing to undo */ } } }
  function finishAnim() { if (Pl.anim) endAnim(); if (Pl.glide) { setScroll(Pl.glide.s, Pl.glide.x1, Pl.glide.y1); Pl.glide = null; } Pl.mom = null; }
  function frame() {
    if (!Pl.open) return;
    if (Pl.stale) refreshState();
    if (!Pl.open) return;
    const t = now();
    runTimers(t);
    if (Pl.glide) { const g = Pl.glide, p = g.dur > 0 ? clamp((t - g.t0) / g.dur, 0, 1) : 1, e = ease(g.ease, p); setScroll(g.s, lerp(g.x0, g.x1, e), lerp(g.y0, g.y1, e)); if (p >= 1) Pl.glide = null; }
    if (Pl.mom) { const m = Pl.mom, dt = Math.min(64, t - m.t); m.t = t; const moved = setScroll(m.s, m.s.sx + m.vx * dt, m.s.sy + m.vy * dt), k = Math.pow(0.995, dt); m.vx *= k; m.vy *= k; if (!moved || Math.hypot(m.vx, m.vy) < 0.02) Pl.mom = null; }
    paint(t);
    if (Pl.settle) { Pl.settle = false; paint(t); }          /* the transition is over: the frame itself, live */
    if (Pl.anim || Pl.hints || Pl.glide || Pl.mom) wake();
  }

  /* ---------------------------------------------------------------- timers ("after a delay") on the player's own clock */
  function clearTimers() { Pl.timers = []; clearTimeout(Pl.timerT); Pl.timerT = 0; }
  function armTimers(extra) {
    clearTimers();
    const top = Pl.overlays.length ? Pl.overlays[Pl.overlays.length - 1].surf : Pl.base; if (!top) return;
    const t0 = now() + (extra || 0);
    for (const e of scan(top.id).after) { const r = reactions(e.node)[e.i]; if (r) Pl.timers.push({at: t0 + rx(r).delay, node: e.node, i: e.i}); }
    scheduleTimers();
  }
  function scheduleTimers() { clearTimeout(Pl.timerT); Pl.timerT = 0; if (!Pl.timers.length || vclock !== null) return; const next = Math.min.apply(null, Pl.timers.map(x => x.at)); Pl.timerT = setTimeout(() => { Pl.timerT = 0; frame(); }, Math.max(0, next - now()) + 2); }
  function runTimers(t) {
    if (!Pl.timers.length) return;
    const due = Pl.timers.filter(x => x.at <= t).sort((p, q) => p.at - q.at)[0];
    if (!due) return;
    const r = reactions(due.node)[due.i];
    Pl.timers = [];
    if (r) perform(due.node, r);
    scheduleTimers();
  }

  /* ---------------------------------------------------------------- the state: base frame, overlays, history */
  function address(frame) {
    const m = /^#\/(f|s)\/([^/?#]+)/.exec(location.hash || '');
    const base = m ? '#/' + m[1] + '/' + m[2] : (HD.app && HD.app.file ? '#/f/' + enc(HD.app.file.id) : '#/');
    return base + (frame ? '/p/' + enc(frame) : '');
  }
  /* the view-only token of this file, when she has switched the share link on (asked of the server, never made here) */
  const shareInfo = {file: null, token: null, at: 0, busy: false};
  function refreshShare(force) {
    const f = HD.app && HD.app.file; if (!f || f.share || !ui.token || shareInfo.busy) return;
    if (!force && shareInfo.file === f.id && Date.now() - shareInfo.at < 3000) return;
    shareInfo.busy = true;
    ui.api('GET', '/files/' + enc(f.id)).then(meta => { shareInfo.file = f.id; shareInfo.token = meta && meta.share && meta.share.role === 'view' && meta.share.token ? String(meta.share.token) : null; }, () => { /* the plain link then */ })
      .then(() => { shareInfo.busy = false; shareInfo.at = Date.now(); });
  }
  /* #/s/<token>/p/<frame> when anyone may view the file (a share link is on, or this IS a share link), else #/f/<id>/p/<frame> */
  function link(frame) {
    frame = frame || (Pl.base && Pl.base.id) || null;
    const f = HD.app && HD.app.file, base = location.origin + location.pathname;
    if (f && !f.share && shareInfo.file === f.id && shareInfo.token) return base + '#/s/' + enc(shareInfo.token) + (frame ? '/p/' + enc(frame) : '');
    return base + address(frame);
  }
  function copyLink(frame) { const url = link(frame); copyText(url, /#\/s\//.test(url) ? 'Prototype link copied. Anyone with the link can watch it.' : 'Prototype link copied. People need to sign in to open it.'); refreshShare(true); }
  function setBase(fid, sx, sy) {
    dropSurface(Pl.base); for (const ov of Pl.overlays) dropSurface(ov.surf); Pl.overlays = [];
    Pl.page = st().pageOf(fid) || Pl.page;
    Pl.L = layoutFor(fid); Pl.base = makeSurface(fid, Pl.L.vw, Pl.L.vh);
    if (Pl.base && (sx || sy)) setScroll(Pl.base, sx || 0, sy || 0);
    try { if (location.hash !== address(fid)) history.replaceState(history.state, '', address(fid)); } catch (e) { /* a sandboxed frame */ }
    syncBar();
  }
  /* after the document or the window changed: the same state, built again */
  function refreshState() {
    Pl.stale = false;
    if (Pl.anim) endAnim(); Pl.glide = null; Pl.mom = null;
    const b = Pl.base;
    if (!b || !N(b.id) || !isScreen(b.id)) {
      const fb = N(Pl.start) && isScreen(Pl.start) ? Pl.start : screens(Pl.page || HD.sel.page)[0];
      if (!fb) { close(); ui.toast('The frame this prototype was showing is gone.'); return; }
      Pl.history = []; setBase(fb); armTimers(0); return;
    }
    const ovs = Pl.overlays.filter(o => N(o.surf.id)).map(o => ({id: o.surf.id, sx: o.surf.sx, sy: o.surf.sy, anim: o.anim}));
    const sx = b.sx, sy = b.sy;
    setBase(b.id, sx, sy);
    for (const o of ovs) { const ov = makeOverlay(o.id, o.anim); if (ov) { setScroll(ov.surf, o.sx, o.sy); Pl.overlays.push(ov); } }
    Pl.history = Pl.history.filter(x => N(x.frame));
  }
  function makeOverlay(id, anim) { const L = Pl.L, n = N(id); if (!n) return null; const ov = {surf: makeSurface(id, Math.min(nv(id, 'w', 100), L.vw), Math.min(nv(id, 'h', 100), L.vh)), conf: overlayConf(id), x: 0, y: 0, anim: anim || null}; placeOverlay(ov); return ov; }
  function reverse(a) { if (!a) return {type: 'instant', dir: 'left', dur: 0, ease: 'out'}; const t = a.type === 'move' ? 'moveout' : a.type === 'moveout' ? 'move' : a.type === 'slide' ? 'slideout' : a.type === 'slideout' ? 'slide' : a.type; return {type: t, dir: t === 'push' || t !== a.type ? OPP[a.dir] || 'right' : a.dir, dur: a.dur, ease: a.ease}; }
  function go(to, anim, o) {
    o = o || {};
    to = N(to) ? (screenOf(to) || null) : null;
    if (!to || !Pl.base) return false;
    finishAnim();
    const from = Pl.base, type = animType(anim);
    if (o.push !== false) { Pl.history.push({frame: from.id, sx: from.sx, sy: from.sy, anim: anim || null}); if (Pl.history.length > 200) Pl.history.shift(); }
    let A = null, fromInfo = null;
    if (type === 'smart') fromInfo = {id: from.id, sx: from.sx, sy: from.sy, fixed: new Set(from.fixed)};
    else if (type !== 'instant') A = snapState();
    setBase(to, o.sx, o.sy);
    if (type === 'smart') Pl.anim = {kind: 'smart', plan: smartPlan(fromInfo, Pl.base), type: type, dur: anim.dur, ease: anim.ease, t0: now(), p: 0};
    else if (A) Pl.anim = {kind: 'screen', A: A, B: snapState(), type: type, dir: anim.dir, dur: anim.dur, ease: anim.ease, t0: now(), p: 0};
    Pl.hover = o.keepHover ? Pl.hover : null;
    armTimers(Pl.anim ? Pl.anim.dur : 0);
    wake(); return true;
  }
  function back(anim) {
    const e = Pl.history.pop(); if (!e) return false;
    if (!N(e.frame)) return back(anim);
    const a = anim && anim.type !== 'instant' ? anim : reverse(e.anim);
    return go(e.frame, a, {push: false, sx: e.sx, sy: e.sy});
  }
  function openOverlay(id, anim, replaceTop) {
    if (!N(id) || !Pl.base) return false;
    finishAnim();
    if (replaceTop && Pl.overlays.length) dropSurface(Pl.overlays.pop().surf);
    const ov = makeOverlay(id, anim); if (!ov) return false;
    const type = animType(anim);
    if (type !== 'instant') Pl.anim = {kind: 'ovin', under: snapState(), ov: {ref: ov, bmp: snapOverlay(ov), x: ov.x, y: ov.y}, type: type, dir: anim.dir, dur: anim.dur, ease: anim.ease, t0: now(), p: 0};
    Pl.overlays.push(ov);
    armTimers(Pl.anim ? Pl.anim.dur : 0); wake(); return true;
  }
  function closeOverlay(anim) {
    if (!Pl.overlays.length) return false;
    finishAnim();
    const ov = Pl.overlays[Pl.overlays.length - 1];
    const own = anim && anim.type !== 'instant', a = own ? anim : (ov.anim || null), type = animType(a);
    if (type !== 'instant') { const bmp = snapOverlay(ov); Pl.overlays.pop(); Pl.anim = {kind: 'ovout', under: snapState(), ov: {ref: ov, bmp: bmp, x: ov.x, y: ov.y}, type: type, dir: a.dir, out: own, dur: a.dur, ease: a.ease, t0: now(), p: 0, after: () => dropSurface(ov.surf)}; }
    else { Pl.overlays.pop(); dropSurface(ov.surf); }
    armTimers(Pl.anim ? Pl.anim.dur : 0); wake(); return true;
  }
  function scrollToNode(id, anim) {
    const s = Pl.overlays.length ? Pl.overlays[Pl.overlays.length - 1].surf : Pl.base, r = rectIn(s, id);
    if (!s || !r) return false;
    finishAnim();
    const x1 = clamp(s.sx + r.x, 0, s.maxX), y1 = clamp(s.sy + r.y, 0, s.maxY), type = animType(anim);
    if (type === 'instant') setScroll(s, x1, y1); else Pl.glide = {s: s, x0: s.sx, y0: s.sy, x1: x1, y1: y1, t0: now(), dur: anim.dur, ease: anim.ease};
    wake(); return true;
  }
  /* run one reaction. Returns a function that takes it back (for "while hovering" / "while pressing"), or null */
  function perform(nodeId, r) {
    const a = rx(r);
    if (a.action === 'navigate') { const before = Pl.base ? {frame: Pl.base.id, sx: Pl.base.sx, sy: Pl.base.sy, n: Pl.history.length} : null; if (!go(a.to, a.anim)) return null; return () => { if (!before || !N(before.frame)) return; Pl.history.length = Math.min(Pl.history.length, before.n); go(before.frame, reverse(a.anim), {push: false, sx: before.sx, sy: before.sy}); }; }
    if (a.action === 'back') { back(a.anim); return null; }
    if (a.action === 'overlay' || a.action === 'swap') {
      if (a.action === 'swap' && !Pl.overlays.length) { if (!N(a.to)) return null; go(a.to, a.anim, {push: false}); return null; }
      const n0 = Pl.overlays.length; if (!openOverlay(a.to, a.anim, a.action === 'swap')) return null;
      return () => { if (Pl.overlays.length > n0 || a.action === 'swap') closeOverlay(null); };
    }
    if (a.action === 'close') { closeOverlay(a.anim); return null; }
    if (a.action === 'scroll') { scrollToNode(a.to, a.anim); return null; }
    if (a.action === 'url') { askLink(a.url); return null; }
    return null;
  }
  function restart() { if (!Pl.open) return; finishAnim(); const s = N(Pl.start) && isScreen(Pl.start) ? Pl.start : screens(Pl.page)[0]; if (!s) return; Pl.history = []; Pl.hover = null; Pl.press = null; setBase(s); armTimers(0); wake(); }
  function step(d) { if (!Pl.open || !Pl.base) return; const all = screens(Pl.page), i = all.indexOf(Pl.base.id), nx = all[i + d]; if (nx) go(nx, {type: 'instant'}, {push: true}); }

  /* ---------------------------------------------------------------- the pointer */
  function surfaceAt(px, py) {
    const L = Pl.L;
    for (let i = Pl.overlays.length - 1; i >= 0; i--) { const ov = Pl.overlays[i], x = L.x + ov.x * L.k, y = L.y + ov.y * L.k; if (px >= x && py >= y && px <= x + ov.surf.vw * L.k && py <= y + ov.surf.vh * L.k) return {s: ov.surf, ox: x, oy: y, top: i === Pl.overlays.length - 1}; return {outside: true}; }
    if (px >= L.x && py >= L.y && px <= L.x + L.w && py <= L.y + L.h) return {s: Pl.base, ox: L.x, oy: L.y, top: true};
    return null;
  }
  function candidates(px, py) { const at = surfaceAt(px, py); if (!at || at.outside || !at.s) return {at: at, s: null, list: EMPTY}; return {at: at, s: at.s, list: hitList(at.s, (px - at.ox) / Pl.L.k, (py - at.oy) / Pl.L.k)}; }
  function cssRect(s, id) { const r = rectIn(s, id); if (!r) return null; const L = Pl.L; let ox = L.x, oy = L.y; for (const ov of Pl.overlays) if (ov.surf === s) { ox = L.x + ov.x * L.k; oy = L.y + ov.y * L.k; } return {x: ox + r.x * L.k, y: oy + r.y * L.k, w: r.w * L.k, h: r.h * L.k}; }
  function pt(ev) { const r = Pl.canvas.getBoundingClientRect(); return [ev.clientX - r.left, ev.clientY - r.top]; }
  function setCursor(c) { if (Pl.cursor !== c) { Pl.cursor = c; Pl.canvas.style.cursor = c; } }
  function flashHints() {
    const s = Pl.overlays.length ? Pl.overlays[Pl.overlays.length - 1].surf : Pl.base; if (!s) return;
    const L = Pl.L, rects = [];
    for (const id of scan(s.id).hot) { const r = cssRect(s, id); if (r) rects.push({x: r.x - L.x, y: r.y - L.y, w: r.w, h: r.h}); }
    Pl.hints = {t0: now(), rects: rects}; wake();
  }
  function onDown(ev) {
    if (!Pl.open || ev.button > 0) return;
    Pl.el.focus({preventScroll: true});
    finishAnim();
    const p = pt(ev), c = candidates(p[0], p[1]);
    try { Pl.canvas.setPointerCapture(ev.pointerId); } catch (e) { /* synthetic */ }
    Pl.down = {x: p[0], y: p[1], lx: p[0], ly: p[1], lt: now(), vx: 0, vy: 0, moved: false, id: ev.pointerId, touch: ev.pointerType === 'touch' || ev.pointerType === 'pen', s: c.s, outside: !!(c.at && c.at.outside),
      click: c.s ? findReaction(c.s, c.list, ['click']) : null, drag: c.s ? findReaction(c.s, c.list, ['drag']) : null, used: false};
    const pr = c.s ? findReaction(c.s, c.list, ['press']) : null;
    if (pr) { Pl.down.used = true; const undo = perform(pr.node, pr.r); Pl.press = {undo: undo}; }
    ev.preventDefault(); wake();
  }
  function onMove(ev) {
    if (!Pl.open) return;
    const p = pt(ev), d = Pl.down;
    if (d && d.id === ev.pointerId) {
      const t = now(), dt = Math.max(1, t - d.lt), dx = p[0] - d.lx, dy = p[1] - d.ly;
      if (!d.moved && Math.hypot(p[0] - d.x, p[1] - d.y) > 8) { d.moved = true; if (d.drag && !d.used) { d.used = true; perform(d.drag.node, d.drag.r); } }
      if (d.moved && d.touch && !d.used && d.s && N(d.s.id)) { const k = Pl.L.k; if (setScroll(d.s, d.s.sx - dx / k, d.s.sy - dy / k)) wake(); d.vx = lerp(d.vx, -dx / k / dt, 0.5); d.vy = lerp(d.vy, -dy / k / dt, 0.5); d.scrolled = true; }
      d.lx = p[0]; d.ly = p[1]; d.lt = t; return;
    }
    if (Pl.anim) return;
    if (Pl.hover) { const r = Pl.hover.rect; if (r && p[0] >= r.x && p[1] >= r.y && p[0] <= r.x + r.w && p[1] <= r.y + r.h) return; leaveHover(); }
    const c = candidates(p[0], p[1]);
    if (!c.s) { setCursor('default'); return; }
    setCursor(findReaction(c.s, c.list, ['click', 'press', 'drag']) ? 'pointer' : 'default');
    const hv = findReaction(c.s, c.list, ['hover']);
    if (hv) { const rect = cssRect(c.s, hv.node); const undo = perform(hv.node, hv.r); Pl.hover = {node: hv.node, rect: rect, undo: undo}; }
  }
  function leaveHover() { const hv = Pl.hover; Pl.hover = null; if (hv && hv.undo) hv.undo(); }
  function onUp(ev) {
    const d = Pl.down; if (!Pl.open || !d || d.id !== ev.pointerId) return;
    Pl.down = null;
    try { Pl.canvas.releasePointerCapture(ev.pointerId); } catch (e) { /* not captured */ }
    if (Pl.press) { const pr = Pl.press; Pl.press = null; if (pr.undo) pr.undo(); return; }
    if (d.scrolled) { if (d.s && Math.hypot(d.vx, d.vy) > 0.05 && now() - d.lt < 80) { Pl.mom = {s: d.s, vx: d.vx, vy: d.vy, t: now()}; wake(); } return; }
    if (d.used || ev.type === 'pointercancel') return;
    const p = pt(ev);
    if (!d.moved || Math.hypot(p[0] - d.x, p[1] - d.y) < 12) {
      if (d.outside) { const top = Pl.overlays[Pl.overlays.length - 1]; if (top && top.conf.closeOutside) closeOverlay(null); return; }
      const c = candidates(p[0], p[1]), hit = c.s ? findReaction(c.s, c.list, ['click']) : null;
      if (hit && d.click && hit.node === d.click.node) { perform(hit.node, hit.r); return; }
      if (c.s || surfaceAt(p[0], p[1])) flashHints();
    }
  }
  function onWheel(ev) {
    if (!Pl.open) return;
    ev.preventDefault();
    const p = pt(ev), at = surfaceAt(p[0], p[1]); let s = at && at.s ? at.s : null;
    if (!s || (s.maxX < 0.5 && s.maxY < 0.5)) { if (at && at.outside) return; s = Pl.overlays.length ? null : Pl.base; }
    if (!s) return;
    let dx = ev.deltaX, dy = ev.deltaY; if (ev.deltaMode === 1) { dx *= 16; dy *= 16; } if (ev.shiftKey && !dx) { dx = dy; dy = 0; }
    Pl.glide = null; Pl.mom = null;
    if (setScroll(s, s.sx + dx / Pl.L.k, s.sy + dy / Pl.L.k)) wake();
  }

  /* ---------------------------------------------------------------- keys */
  function keyHit(ev) {
    const s = Pl.overlays.length ? Pl.overlays[Pl.overlays.length - 1].surf : Pl.base; if (!s) return null;
    const k = ev.key.length === 1 ? ev.key.toLowerCase() : ev.key;
    for (const e of scan(s.id).keys) { const r = reactions(e.node)[e.i]; if (!r) continue; const want = rx(r).key; if (want && (want.length === 1 ? want.toLowerCase() : want) === k) return {node: e.node, r: r}; }
    return null;
  }
  function onKey(ev) {
    if (!Pl.open) return;
    const inPop = !!(ev.target && ev.target.closest && ev.target.closest('.hd-pop'));
    if (inPop && /^(Arrow|Home$|End$|Tab$|Enter$| $)/.test(ev.key)) { ev.stopPropagation(); return; }      /* a menu of the player: its own keys only */
    ev.stopImmediatePropagation();
    if (Pl.ask) { if (ev.key === 'Escape') { ev.preventDefault(); closeAsk(); } return; }
    if (ev.key === 'Escape') { ev.preventDefault(); if (document.querySelector('.hd-pop')) { ui.closePops(0); return; } close(); return; }
    if (typing(ev) || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    const onButton = ev.target && ev.target.tagName === 'BUTTON' && (ev.key === 'Enter' || ev.key === ' ');
    if (inPop) return;
    if (!onButton) { const kh = keyHit(ev); if (kh) { ev.preventDefault(); finishAnim(); perform(kh.node, kh.r); return; } }
    if (onButton) return;
    const k = ev.key.toLowerCase();
    if (k === 'r') { ev.preventDefault(); restart(); }
    else if (k === 'f') { ev.preventDefault(); fullscreen(); }
    else if (ev.key === 'ArrowRight' || ev.key === ' ') { ev.preventDefault(); step(1); }
    else if (ev.key === 'ArrowLeft') { ev.preventDefault(); step(-1); }
    else if (ev.key === 'Backspace') { ev.preventDefault(); back(null); }
  }
  function swallow(ev) { if (Pl.open) ev.stopImmediatePropagation(); }
  function fullscreen() { try { if (document.fullscreenElement) document.exitFullscreen(); else if (Pl.el.requestFullscreen) Pl.el.requestFullscreen().catch(() => {}); } catch (e) { /* not allowed here */ } }

  /* ---------------------------------------------------------------- "open link": ask first, https only */
  function closeAsk() { if (Pl.ask && Pl.ask.parentNode) Pl.ask.parentNode.removeChild(Pl.ask); Pl.ask = null; if (Pl.el) Pl.el.focus({preventScroll: true}); }
  function askLink(url) {
    closeAsk();
    const href = safeLink(url);
    if (!href) { ui.toast('This link is not a secure https address, so it was not opened.', true); return; }
    const stay = h('button', {class: 'hd-btn', type: 'button', text: 'Stay here', on: {click: closeAsk}});
    const goBtn = h('button', {class: 'hd-btn pri', type: 'button', text: 'Open the link', on: {click: () => { closeAsk(); try { window.open(href, '_blank', 'noopener,noreferrer'); } catch (e) { /* blocked */ } }}});
    Pl.ask = h('div', {class: 'hdp-ask', role: 'alertdialog', 'aria-modal': 'true', 'aria-label': 'Open a link'},
      h('div', {class: 'hdp-askbox'}, h('h2', {text: 'Leave the prototype?'}), h('p', {text: 'This prototype wants to open a link in a new tab:'}), h('p', {class: 'hdp-url', text: href}), h('div', {class: 'hdp-askbtns'}, stay, goBtn)));
    Pl.el.appendChild(Pl.ask); stay.focus();
  }

  /* ---------------------------------------------------------------- the toolbar */
  function copyText(text, msg) {
    const done = () => ui.toast(msg || 'Prototype link copied.');
    const old = () => { const ta = h('textarea', {class: 'hdp-clip', 'aria-hidden': 'true', tabIndex: -1}); ta.value = text; document.body.appendChild(ta); ta.select(); let ok = false; try { ok = document.execCommand('copy'); } catch (e) { ok = false; } document.body.removeChild(ta); if (ok) done(); else ui.toast('The link could not be copied: ' + text, true); };
    try { if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(text).then(done, old); return; } } catch (e) { /* the old way */ }
    old();
  }
  function flowOf(fid) { const fl = flows(Pl.page); return fl.find(f => f.id === fid) || fl.find(f => f.id === Pl.start) || null; }
  function syncBar() {
    const b = Pl.bar; if (!Pl.open || !b.name) return;
    const all = screens(Pl.page), i = Pl.base ? all.indexOf(Pl.base.id) : -1, fl = flows(Pl.page), cur = flowOf(Pl.base && Pl.base.id);
    b.name.textContent = Pl.base ? nameOf(Pl.base.id) : '';
    b.count.textContent = (i >= 0 ? i + 1 : 1) + ' / ' + Math.max(1, all.length);
    b.prev.disabled = i <= 0; b.next.disabled = i < 0 || i >= all.length - 1;
    b.flow.hidden = fl.length < 2; b.flowName.textContent = cur ? cur.name : 'Flows';
    for (const z of b.zoom.children) { const on = z.dataset.v === Pl.zoom; z.classList.toggle('on', on); z.setAttribute('aria-checked', String(on)); }
  }
  function buildBar() {
    const b = Pl.bar = {};
    const ib = (ic, title, run) => { const x = h('button', {class: 'hd-ib', type: 'button', title: title, 'aria-label': title}, icon(ic)); x.addEventListener('click', run); return x; };
    b.exit = h('button', {class: 'hd-btn', type: 'button', title: 'Close the prototype (Esc)', on: {click: () => close()}}, icon('close'), h('span', {text: ui.mounted && canEdit() ? 'Back to the editor' : 'Close'}));
    b.flowName = h('span', {text: 'Flows'});
    b.flow = h('button', {class: 'hd-btn hdp-flow', type: 'button', title: 'Choose a flow', 'aria-haspopup': 'menu', hidden: true}, icon('play'), b.flowName, icon('down'));
    b.flow.addEventListener('click', () => { const cur = flowOf(Pl.base && Pl.base.id); ui.menu(b.flow, flows(Pl.page).map(f => ({label: f.name, checked: !!cur && cur.id === f.id, run: () => { Pl.start = f.id; restart(); }})), {label: 'Flows'}); });
    b.name = h('span', {class: 'hdp-name'});
    b.prev = ib('back', 'Previous frame (Left arrow)', () => step(-1)); b.next = ib('right', 'Next frame (Right arrow)', () => step(1)); b.count = h('span', {class: 'hdp-count', 'aria-live': 'polite'});
    b.restart = ib('rotate', 'Restart (R)', restart);
    b.zoom = h('div', {class: 'hd-seg', role: 'radiogroup', 'aria-label': 'Size'});
    for (const z of [['fit', 'Fit', 'Fit the whole frame in the window'], ['fill', 'Fill', 'Fill the width of the window'], ['100', '100%', 'Actual size']]) b.zoom.appendChild(h('button', {class: 'hd-segb', type: 'button', role: 'radio', 'data-v': z[0], title: z[2], text: z[1], on: {click: () => { Pl.zoom = z[0]; Pl.stale = true; syncBar(); wake(); if (vclock !== null) frame(); }}}));
    b.link = h('button', {class: 'hd-btn', type: 'button', title: 'Copy a link to this prototype', on: {click: () => copyLink()}}, icon('link'), h('span', {text: 'Copy link'}));
    b.full = ib('corners', 'Full screen (F)', fullscreen);
    return h('header', {class: 'hdp-bar'}, h('div', {class: 'hdp-l'}, b.exit, b.flow, b.name), h('div', {class: 'hdp-c'}, b.prev, b.count, b.next, b.restart), h('div', {class: 'hdp-r'}, b.zoom, b.link, b.full));
  }
  function resize() {
    if (!Pl.open) return;
    const r = Pl.stage.getBoundingClientRect(), d = Math.max(1, Math.min(3, window.devicePixelRatio || 1)), w = Math.max(1, Math.round(r.width)), hh = Math.max(1, Math.round(r.height));
    if (w === Pl.W && hh === Pl.H && d === Pl.dpr) return;
    Pl.W = w; Pl.H = hh; Pl.dpr = d; Pl.canvas.width = Math.round(w * d); Pl.canvas.height = Math.round(hh * d);
    if (Pl.base) { Pl.stale = true; if (vclock !== null) frame(); else wake(); }
  }

  /* ---------------------------------------------------------------- open / close */
  function open(frameId) {
    if (!HD.store || !st().pages().length) return false;
    let fid = frameId && N(frameId) ? screenOf(frameId) : null;
    const page = fid ? st().pageOf(fid) : ((frameId && N(frameId) && st().pageOf(frameId)) || HD.sel.page || st().pages()[0]);
    if (!fid) { const fl = flows(page); fid = fl.length ? fl[0].id : (screens(page)[0] || null); if (frameId && !N(frameId) && fid) ui.toast('That frame is no longer in this file. The prototype starts at the first one.'); }
    if (!fid) { ui.toast('Draw a frame first: a prototype plays frames.'); try { if (/\/p\//.test(location.hash)) history.replaceState(history.state, '', address(null)); } catch (e) { /* fine */ } return false; }
    if (Pl.open) { if (!Pl.base || Pl.base.id !== fid) go(fid, {type: 'instant'}, {push: true}); return true; }
    ui.closePops(0); edClose(); W.sel = null; refreshShare(true);
    Pl.canvas = h('canvas', {class: 'hdp-canvas', 'aria-label': 'Prototype. Click the screen to use it.'});
    Pl.stage = h('div', {class: 'hdp-stage'}, Pl.canvas);
    Pl.el = h('div', {class: 'hdp', role: 'dialog', 'aria-label': 'Prototype player', tabIndex: -1}, buildBar(), Pl.stage);
    document.body.appendChild(Pl.el);
    Pl.ctx = Pl.canvas.getContext('2d');
    Pl.open = true; Pl.page = page; Pl.start = fid; Pl.history = []; Pl.overlays = []; Pl.base = null; Pl.anim = null; Pl.hints = null; Pl.hover = null; Pl.press = null; Pl.down = null; Pl.W = 0; Pl.H = 0; Pl.cursor = '';
    Pl.pushed = false;
    try { if (!/\/p\/[^/]+/.test(location.hash)) { history.pushState(history.state, '', address(fid)); Pl.pushed = true; } } catch (e) { /* a sandboxed frame */ }
    const cv = Pl.canvas, on = (t, ev, fn, o) => { t.addEventListener(ev, fn, o); Pl.offs.push(() => t.removeEventListener(ev, fn, o)); };
    on(cv, 'pointerdown', onDown); on(cv, 'pointermove', onMove); on(cv, 'pointerup', onUp); on(cv, 'pointercancel', onUp); on(cv, 'pointerleave', () => { if (!Pl.down) { leaveHover(); setCursor('default'); } });
    on(cv, 'wheel', onWheel, {passive: false}); on(cv, 'contextmenu', ev => ev.preventDefault());
    on(window, 'keydown', onKey, true); on(window, 'keyup', swallow, true); on(window, 'paste', swallow, true); on(window, 'cut', swallow, true); on(window, 'copy', swallow, true);
    on(window, 'resize', resize);
    if (typeof ResizeObserver === 'function') { Pl.ro = new ResizeObserver(resize); Pl.ro.observe(Pl.stage); }
    const r = Pl.stage.getBoundingClientRect(); Pl.dpr = Math.max(1, Math.min(3, window.devicePixelRatio || 1)); Pl.W = Math.max(1, Math.round(r.width)); Pl.H = Math.max(1, Math.round(r.height)); cv.width = Math.round(Pl.W * Pl.dpr); cv.height = Math.round(Pl.H * Pl.dpr);
    setBase(fid); armTimers(0);
    Pl.el.focus({preventScroll: true});
    frame();
    try { HD.render.ready(fid, 4000).then(() => { if (Pl.open) { if (vclock !== null) frame(); else wake(); } }); } catch (e) { /* drawn as it is */ }
    return true;
  }
  function close(fromHistory) {
    if (!Pl.open) return;
    Pl.open = false; clearTimers(); closeAsk();
    if (Pl.raf) { cancelAnimationFrame(Pl.raf); Pl.raf = 0; }
    for (const f of Pl.offs.splice(0)) { try { f(); } catch (e) { /* gone */ } }
    if (Pl.ro) { try { Pl.ro.disconnect(); } catch (e) { /* gone */ } Pl.ro = null; }
    try { if (document.fullscreenElement === Pl.el) document.exitFullscreen(); } catch (e) { /* not in full screen */ }
    dropSurface(Pl.base); for (const ov of Pl.overlays) dropSurface(ov.surf);
    Pl.base = null; Pl.overlays = []; Pl.anim = null; Pl.history = []; Pl.hints = null; Pl.hover = null; Pl.press = null; Pl.down = null; Pl.mom = null; Pl.glide = null;
    scratch.keep.clear(); scratch.keepKids.clear(); scratch.temp.clear(); scratch.tempKids.clear();
    if (Pl.el && Pl.el.parentNode) Pl.el.parentNode.removeChild(Pl.el);
    Pl.el = null; Pl.canvas = null; Pl.ctx = null; Pl.stage = null; Pl.bar = {};
    if (!fromHistory) { try { if (Pl.pushed && /\/p\/[^/]+/.test(location.hash)) history.back(); else if (/\/p\/[^/]+/.test(location.hash)) history.replaceState(history.state, '', address(null)); } catch (e) { /* fine */ } }
    Pl.pushed = false;
    if (scratch.made > 2000) flushScratch();
    if (ui.mounted) { try { if (HD.tools.canvas) HD.tools.canvas.focus({preventScroll: true}); HD.render.invalidate(); } catch (e) { /* the editor is gone */ } ui.refresh(); }
  }
  window.addEventListener('hashchange', () => { if (Pl.open && !/^#\/(f|s)\/[^/?#]+\/p\/[^/?#]+/.test(location.hash || '')) close(true); });
  ui.hook('present', id => { open(id || null); });

  /* ================================================================ the editor: wiring on the canvas */
  const W = {sel: null, drag: null, conns: null, ver: 0, page: null};
  let ed = null;
  function protoTab() { return !!(ui.mounted && ui.state && ui.state.rightTab === 'prototype' && !Pl.open); }
  function connsOf(page) {
    if (W.conns && W.ver === docVer && W.page === page) return W.conns;
    const out = []; let count = 0;
    if (page && N(page)) st().walk(page, (id, n) => { if (++count > 30000 || !n || n.visible === false) return false; const list = reactions(id); for (let i = 0; i < list.length; i++) { const a = rx(list[i]); out.push({node: id, i: i, a: a, to: NEEDS_TO[a.action] && a.to && N(a.to) && st().pageOf(a.to) === page ? a.to : null}); } return true; });
    W.conns = out; W.ver = docVer; W.page = page; return out;
  }
  function sRect(id) { const b = st().worldBounds(id), p = HD.render.worldToScreen(b.x, b.y), z = HD.render.view.zoom || 1; return {x: p[0], y: p[1], w: b.w * z, h: b.h * z}; }
  function curve(s, t) {
    const sc = [s.x + s.w / 2, s.y + s.h / 2], tc = [t.x + t.w / 2, t.y + t.h / 2]; let p0, p3, d;
    if (t.x >= s.x + s.w - 4) { p0 = [s.x + s.w, sc[1]]; p3 = [t.x, clamp(sc[1], t.y + Math.min(16, t.h / 2), t.y + t.h - Math.min(16, t.h / 2))]; d = [1, 0, -1, 0]; }
    else if (t.x + t.w <= s.x + 4) { p0 = [s.x, sc[1]]; p3 = [t.x + t.w, clamp(sc[1], t.y + Math.min(16, t.h / 2), t.y + t.h - Math.min(16, t.h / 2))]; d = [-1, 0, 1, 0]; }
    else if (tc[1] >= sc[1]) { p0 = [sc[0], s.y + s.h]; p3 = [clamp(sc[0], t.x + Math.min(16, t.w / 2), t.x + t.w - Math.min(16, t.w / 2)), t.y]; d = [0, 1, 0, -1]; }
    else { p0 = [sc[0], s.y]; p3 = [clamp(sc[0], t.x + Math.min(16, t.w / 2), t.x + t.w - Math.min(16, t.w / 2)), t.y + t.h]; d = [0, -1, 0, 1]; }
    const c = clamp(Math.hypot(p3[0] - p0[0], p3[1] - p0[1]) * 0.4, 24, 180);
    return [p0, [p0[0] + d[0] * c, p0[1] + d[1] * c], [p3[0] + d[2] * c, p3[1] + d[3] * c], p3];
  }
  function bezAt(b, t) { const u = 1 - t, a = u * u * u, c = 3 * u * u * t, d = 3 * u * t * t, e = t * t * t; return [a * b[0][0] + c * b[1][0] + d * b[2][0] + e * b[3][0], a * b[0][1] + c * b[1][1] + d * b[2][1] + e * b[3][1]]; }
  /* the arrows of the page as the overlay draws them: [{node, i, to, pts (screen bezier) | null, stub}] */
  function wires() {
    const page = HD.sel.page, out = [];
    for (const c of connsOf(page)) {
      if (!N(c.node)) continue;
      const s = sRect(c.node);
      if (c.to) out.push({node: c.node, i: c.i, to: c.to, a: c.a, pts: curve(s, sRect(c.to))});
      else out.push({node: c.node, i: c.i, to: null, a: c.a, pts: null, stub: [s.x + s.w, s.y + s.h / 2]});
    }
    return out;
  }
  function handle() { const ids = HD.sel.ids || EMPTY; if (ids.length !== 1 || !N(ids[0]) || !canEdit()) return null; const n = N(ids[0]); if (n.type === 'PAGE' || n.type === 'SECTION') return null; const s = sRect(ids[0]); return {node: ids[0], x: s.x + s.w + 14, y: s.y + s.h / 2}; }
  function badges() { const out = []; for (const f of flows(HD.sel.page)) { const s = sRect(f.id); out.push({id: f.id, name: f.name, x: s.x, y: s.y}); } return out; }
  function arrowHead(ctx, b, col) { const p = b[3], q = bezAt(b, 0.94), a = Math.atan2(p[1] - q[1], p[0] - q[0]); ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(p[0] - 9 * Math.cos(a - 0.42), p[1] - 9 * Math.sin(a - 0.42)); ctx.lineTo(p[0] - 9 * Math.cos(a + 0.42), p[1] - 9 * Math.sin(a + 0.42)); ctx.closePath(); ctx.fillStyle = col; ctx.fill(); }
  const badgeBoxes = [];
  function drawWires(ctx) {
    badgeBoxes.length = 0;
    if (!protoTab()) return;
    ctx.save(); ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    const list = wires(), isSel = w => W.sel && W.sel.node === w.node && W.sel.i === w.i;
    for (const pass of [0, 1]) for (const w of list) {
      const on = isSel(w); if ((pass === 1) !== !!on) continue;
      const col = ACC;
      if (w.pts) {
        const b = w.pts;
        if (on) { ctx.beginPath(); ctx.moveTo(b[0][0], b[0][1]); ctx.bezierCurveTo(b[1][0], b[1][1], b[2][0], b[2][1], b[3][0], b[3][1]); ctx.strokeStyle = 'rgba(110,85,240,0.25)'; ctx.lineWidth = 7; ctx.stroke(); }
        ctx.beginPath(); ctx.moveTo(b[0][0], b[0][1]); ctx.bezierCurveTo(b[1][0], b[1][1], b[2][0], b[2][1], b[3][0], b[3][1]);
        ctx.setLineDash(w.a.action === 'navigate' ? [] : [6, 5]); ctx.strokeStyle = col; ctx.lineWidth = on ? 2.5 : 1.75; ctx.stroke(); ctx.setLineDash([]);
        arrowHead(ctx, b, col);
        ctx.beginPath(); ctx.arc(b[0][0], b[0][1], 4, 0, Math.PI * 2); ctx.fillStyle = '#FFFFFF'; ctx.fill(); ctx.lineWidth = 1.75; ctx.strokeStyle = col; ctx.stroke();
      } else if (pass === 0) {       /* nowhere to point (back, close, a link): a short stub with a dot */
        const p = w.stub; ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(p[0] + 16, p[1]); ctx.strokeStyle = col; ctx.lineWidth = 1.75; ctx.stroke();
        ctx.beginPath(); ctx.arc(p[0] + 20, p[1], 4, 0, Math.PI * 2); ctx.fillStyle = col; ctx.fill();
      }
    }
    /* flow starting points */
    ctx.font = '600 12px "Schibsted Grotesk", system-ui, sans-serif'; ctx.textBaseline = 'middle';
    for (const b of badges()) {
      const text = b.name.length > 22 ? b.name.slice(0, 21) + '\u2026' : b.name, tw = Math.ceil(ctx.measureText(text).width), bw = tw + 30, bh = 22, x = Math.round(b.x), y = Math.round(b.y - 46);
      rr(ctx, x, y, bw, bh, 6); ctx.fillStyle = ACC; ctx.fill();
      ctx.beginPath(); ctx.moveTo(x + 9, y + 6.5); ctx.lineTo(x + 17, y + 11); ctx.lineTo(x + 9, y + 15.5); ctx.closePath(); ctx.fillStyle = '#FFFFFF'; ctx.fill();
      ctx.fillText(text, x + 22, y + bh / 2 + 0.5);
      badgeBoxes.push({id: b.id, x: x, y: y, w: bw, h: bh});
    }
    /* the wire being dragged, then the + handle */
    const d = W.drag;
    if (d) {
      if (d.target && N(d.target)) { const t = sRect(d.target); ctx.strokeStyle = ACC; ctx.lineWidth = 2.5; ctx.strokeRect(t.x - 1, t.y - 1, t.w + 2, t.h + 2); }
      const s = sRect(d.node), b = d.target && N(d.target) ? curve(s, sRect(d.target)) : null;
      ctx.beginPath();
      if (b) { ctx.moveTo(b[0][0], b[0][1]); ctx.bezierCurveTo(b[1][0], b[1][1], b[2][0], b[2][1], b[3][0], b[3][1]); }
      else { const p0 = [s.x + s.w, s.y + s.h / 2], c = clamp(Math.abs(d.x - p0[0]) * 0.4, 20, 160); ctx.moveTo(p0[0], p0[1]); ctx.bezierCurveTo(p0[0] + c, p0[1], d.x - c, d.y, d.x, d.y); }
      ctx.strokeStyle = ACC; ctx.lineWidth = 2; ctx.stroke();
      if (b) arrowHead(ctx, b, ACC); else { ctx.beginPath(); ctx.arc(d.x, d.y, 4, 0, Math.PI * 2); ctx.fillStyle = ACC; ctx.fill(); }
    } else {
      const hd = handle();
      if (hd) { ctx.beginPath(); ctx.arc(hd.x, hd.y, 8, 0, Math.PI * 2); ctx.fillStyle = '#FFFFFF'; ctx.fill(); ctx.lineWidth = 1.75; ctx.strokeStyle = ACC; ctx.stroke(); ctx.beginPath(); ctx.moveTo(hd.x - 4, hd.y); ctx.lineTo(hd.x + 4, hd.y); ctx.moveTo(hd.x, hd.y - 4); ctx.lineTo(hd.x, hd.y + 4); ctx.lineWidth = 1.75; ctx.stroke(); }
    }
    ctx.restore();
  }
  HD.render.addOverlay(drawWires);
  function wireAt(sx, sy) { let best = null, bd = 7; for (const w of wires()) { if (w.pts) { for (let i = 0; i <= 28; i++) { const p = bezAt(w.pts, i / 28), d = Math.hypot(p[0] - sx, p[1] - sy); if (d < bd) { bd = d; best = w; } } } else if (Math.hypot(w.stub[0] + 18 - sx, w.stub[1] - sy) < 8) return w; } return best; }
  function screenAt(wx, wy, not) { const all = screens(HD.sel.page); for (let i = all.length - 1; i >= 0; i--) { if (all[i] === not) continue; const b = st().worldBounds(all[i]); if (wx >= b.x && wy >= b.y && wx <= b.x + b.w && wy <= b.y + b.h) return all[i]; } return null; }
  function canvasPt(ev) { const r = HD.tools.canvas.getBoundingClientRect(); return [ev.clientX - r.left, ev.clientY - r.top]; }
  function wireMove(ev) {
    const d = W.drag; if (!d) return;
    ev.stopPropagation(); ev.preventDefault();
    const p = canvasPt(ev), w = HD.render.screenToWorld(p[0], p[1]);
    d.x = p[0]; d.y = p[1]; d.target = screenAt(w[0], w[1], d.own); d.moved = d.moved || Math.hypot(p[0] - d.x0, p[1] - d.y0) > 4;
    HD.render.invalidate();
  }
  function wireUp(ev) {
    const d = W.drag; if (!d) return;
    ev.stopPropagation(); ev.preventDefault();
    window.removeEventListener('pointermove', wireMove, true); window.removeEventListener('pointerup', wireUp, true); window.removeEventListener('pointercancel', wireUp, true);
    W.drag = null; document.body.classList.remove('hd-dragging');
    if (ev.type !== 'pointercancel' && d.target && N(d.target) && N(d.node)) {
      const i = addReaction(d.node, {trigger: 'click', action: 'navigate', to: d.target, anim: {type: 'dissolve', dir: 'left', dur: 300, ease: 'out'}});
      if (i >= 0) W.sel = {node: d.node, i: i};
    } else if (ev.type !== 'pointercancel' && d.moved) ui.toast('Drop the connector on a frame to link to it.');
    HD.render.invalidate(); ui.refresh();
  }
  document.addEventListener('pointerdown', ev => {
    if (Pl.open || !ui.mounted || ev.button !== 0 || !HD.tools || ev.target !== HD.tools.canvas || !protoTab() || HD.tools.current !== 'move' || HD.tools.panOnly) return;
    const p = canvasPt(ev);
    for (const b of badgeBoxes) if (p[0] >= b.x && p[1] >= b.y && p[0] <= b.x + b.w && p[1] <= b.y + b.h) { ev.stopPropagation(); ev.preventDefault(); open(b.id); return; }
    const hd = handle();
    if (hd && Math.hypot(p[0] - hd.x, p[1] - hd.y) <= 11) {
      ev.stopPropagation(); ev.preventDefault(); edClose();
      W.sel = null; W.drag = {node: hd.node, own: screenOf(hd.node), x: p[0], y: p[1], x0: p[0], y0: p[1], target: null, moved: false};
      document.body.classList.add('hd-dragging');
      window.addEventListener('pointermove', wireMove, true); window.addEventListener('pointerup', wireUp, true); window.addEventListener('pointercancel', wireUp, true);
      HD.render.invalidate(); return;
    }
    const w = wireAt(p[0], p[1]);
    if (w) {
      ev.stopPropagation(); ev.preventDefault();
      W.sel = {node: w.node, i: w.i};
      if (!(HD.sel.ids.length === 1 && HD.sel.ids[0] === w.node)) { HD.sel.set([w.node]); W.sel = {node: w.node, i: w.i}; }
      HD.render.invalidate(); ui.refresh();
      edOpen({x: ev.clientX + 12, y: ev.clientY + 12}, w.node, w.i);
      return;
    }
    if (W.sel) { W.sel = null; HD.render.invalidate(); ui.refresh(); }
  }, true);
  window.addEventListener('keydown', ev => {
    if (Pl.open || !W.sel || !protoTab() || typing(ev) || (ev.target && ev.target.closest && ev.target.closest('.hd-pop'))) return;
    if (ev.key === 'Delete' || ev.key === 'Backspace') {
      ev.stopImmediatePropagation(); ev.preventDefault();
      const s = W.sel; W.sel = null; edClose(); if (canEdit()) removeReaction(s.node, s.i);
      HD.render.invalidate(); ui.refresh();
    } else if (ev.key === 'Escape') { W.sel = null; HD.render.invalidate(); ui.refresh(); }
  }, true);

  /* ================================================================ the editor: one interaction, in a popover */
  function edClose() { if (ed && ed.pop) { const p = ed.pop; ed = null; p.close(); } ed = null; }
  function edOpen(anchor, id, i, side) {
    edClose();
    const me = {id: id, i: i, box: h('div', {class: 'hdp-ed'}), pop: null, q: ''};
    ed = me; edRender();
    me.pop = ui.pop(anchor, me.box, {cls: 'hdp-pop', label: 'Interaction', side: side || 'left', onClose: () => { if (ed === me) { ed = null; ui.refresh(); } }});
    ed = me;
  }
  function frow(text, control) { return h('div', {class: 'hdp-row'}, h('span', {class: 'hdp-lab', text: text}), control); }
  function pick(opts, value, set, lbl, key) { const el = h('select', {class: 'hd-sel', 'aria-label': lbl, title: lbl, 'data-k': key || lbl, disabled: !canEdit()}); for (const o of opts) el.appendChild(h('option', {value: o[0], text: o[1]})); el.value = value; el.addEventListener('change', () => set(el.value)); return el; }
  function numIn(value, set, lbl, o) {
    o = o || {}; const el = h('input', {class: 'hd-in', type: 'text', inputmode: 'decimal', 'aria-label': lbl, title: lbl, 'data-k': o.key || lbl, value: String(value) + (o.unit || ''), disabled: !canEdit(), spellcheck: 'false', autocomplete: 'off'});
    el.addEventListener('focus', () => setTimeout(() => { if (document.activeElement === el) el.select(); }, 0));
    el.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); el.blur(); } });
    el.addEventListener('change', () => { let v = parseFloat(String(el.value).replace(',', '.')); if (!isFinite(v)) { el.value = String(value) + (o.unit || ''); return; } v = clamp(v, o.min === undefined ? -1e6 : o.min, o.max === undefined ? 1e6 : o.max); if (o.int) v = Math.round(v); el.value = String(v) + (o.unit || ''); if (v !== value) set(v); });
    return el;
  }
  function edRender() {
    const me = ed; if (!me) return;
    const r0 = reactions(me.id)[me.i];
    if (!r0 || !N(me.id)) { edClose(); return; }
    const a = rx(r0), box = me.box, edit = canEdit(), keep = document.activeElement && box.contains(document.activeElement) ? document.activeElement.getAttribute('data-k') : null;
    const upd = (fn, lbl) => { patchReaction(me.id, me.i, fn, lbl); edRender(); HD.render.invalidate(); ui.refresh(); };
    clear(box);
    box.appendChild(h('div', {class: 'hdp-edhead'}, h('h3', {text: 'Interaction'}), h('span', {class: 'hdp-edfrom', text: nameOf(me.id)})));
    box.appendChild(frow('Trigger', pick(TRIGGERS, a.trigger, v => upd(r => { r.trigger = v; if (v === 'after') r.delay = num(r.delay, 800); else delete r.delay; if (v !== 'key') delete r.key; }, 'Change trigger'), 'Trigger')));
    if (a.trigger === 'after') box.appendChild(frow('Delay', numIn(a.delay, v => upd(r => { r.delay = v; }, 'Change delay'), 'Delay in milliseconds', {min: 0, max: 600000, int: true, unit: 'ms'})));
    if (a.trigger === 'key') {
      const kb = h('button', {class: 'hd-btn hdp-key', type: 'button', 'data-k': 'key', disabled: !edit, text: a.key ? keyLabel(a.key) : 'Press a key\u2026', title: 'Click, then press the key'});
      kb.addEventListener('click', () => { kb.textContent = 'Press a key\u2026'; kb.classList.add('on'); });
      kb.addEventListener('keydown', ev => { if (!kb.classList.contains('on')) return; ev.preventDefault(); ev.stopPropagation(); if (ev.key === 'Escape' || ev.key === 'Shift' || ev.key === 'Control' || ev.key === 'Alt' || ev.key === 'Meta') { if (ev.key === 'Escape') edRender(); return; } const k = ev.key; upd(r => { r.key = k; }, 'Change key'); });
      kb.addEventListener('blur', () => kb.classList.remove('on'));
      box.appendChild(frow('Key', kb));
    }
    box.appendChild(frow('Action', pick(ACTIONS, a.action, v => upd(r => { r.action = v; if (!NEEDS_TO[v]) delete r.to; else if (v === 'scroll') { if (!r.to || screenOf(r.to) !== screenOf(me.id) || isScreen(r.to)) delete r.to; } else if (!r.to || !isScreen(r.to)) { const t = defaultTarget(me.id); if (t) r.to = t; else delete r.to; }
      if (v !== 'url') delete r.url; if (!HAS_ANIM[v]) delete r.anim; else if (!r.anim) r.anim = {type: v === 'scroll' ? 'smart' : 'dissolve', dir: 'left', dur: 300, ease: 'out'}; }, 'Change action'), 'Action')));
    if (NEEDS_TO[a.action]) {
      const own = screenOf(me.id), page = st().pageOf(me.id); let items;
      if (a.action === 'scroll') { items = []; let c = 0; if (own) st().walk(own, (id, n, d) => { if (id === own) return true; if (++c > 400 || !n || n.visible === false) return false; items.push({id: id, name: n.name || n.type, type: n.type}); return d < 4; }); }
      else items = screens(page).filter(s => s !== own || a.action !== 'navigate').map(s => ({id: s, name: nameOf(s), type: 'FRAME'}));
      const q = h('input', {class: 'hd-in', type: 'search', placeholder: a.action === 'scroll' ? 'Find a layer' : 'Find a frame', 'aria-label': 'Find a destination', 'data-k': 'q', value: me.q, spellcheck: 'false', autocomplete: 'off'});
      const list = h('div', {class: 'hdp-dest', role: 'listbox', 'aria-label': 'Destination'});
      const fill = () => { clear(list); const f = me.q.trim().toLowerCase(), shown = items.filter(it => !f || it.name.toLowerCase().indexOf(f) >= 0).slice(0, 200);
        if (!shown.length) { list.appendChild(h('p', {class: 'hd-note', text: items.length ? 'Nothing with that name.' : a.action === 'scroll' ? 'This frame has no layers to scroll to.' : 'Add another frame to this page first.'})); return; }
        for (const it of shown) { const on = it.id === a.to; const b = h('button', {class: 'hdp-di' + (on ? ' on' : ''), type: 'button', role: 'option', 'aria-selected': String(on), disabled: !edit, 'data-id': it.id, 'data-k': 'd' + it.id}, icon(it.type === 'TEXT' ? 'text' : it.type === 'FRAME' || it.type === 'COMPONENT' ? 'frame' : 'rect', 14), h('span', {text: it.name}), on ? icon('check', 14) : null); b.addEventListener('click', () => upd(r => { r.to = it.id; }, 'Change destination')); list.appendChild(b); } };
      q.addEventListener('input', () => { me.q = q.value; fill(); }); q.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); const b = list.querySelector('.hdp-di'); if (b) b.click(); } });
      fill();
      box.appendChild(h('div', {class: 'hdp-destbox'}, h('span', {class: 'hdp-lab', text: 'Destination'}), items.length > 6 ? q : null, list));
    }
    if (a.action === 'url') {
      const u = h('input', {class: 'hd-in', type: 'url', placeholder: 'https://example.com', 'aria-label': 'Link address', 'data-k': 'url', value: a.url, disabled: !edit, spellcheck: 'false', autocomplete: 'off'});
      u.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); u.blur(); } });
      u.addEventListener('change', () => { let v = u.value.trim(); if (!v) { upd(r => { delete r.url; }, 'Change link'); return; } if (!/^[a-z][a-z0-9+.-]*:/i.test(v)) v = 'https://' + v; const ok = safeLink(v); if (!ok) { ui.toast('Only secure https links can be opened from a prototype.', true); u.value = a.url; return; } upd(r => { r.url = ok; }, 'Change link'); });
      box.appendChild(frow('Link', u));
      box.appendChild(h('p', {class: 'hd-note', text: 'The viewer is asked before the link opens, in a new tab. Only https links work.'}));
    }
    if (HAS_ANIM[a.action]) {
      const setA = (fn, lbl) => upd(r => { r.anim = Object.assign({type: 'instant', dir: 'left', dur: 300, ease: 'out'}, r.anim && typeof r.anim === 'object' ? r.anim : null); fn(r.anim); }, lbl);
      const types = a.action === 'scroll' ? [['instant', 'Instant'], ['smart', 'Animate']] : a.action === 'navigate' || a.action === 'back' ? ANIMS : ANIMS.filter(x => x[0] !== 'push' && x[0] !== 'smart' && x[0] !== 'slide' && x[0] !== 'slideout');
      const cur = types.some(x => x[0] === a.anim.type) ? a.anim.type : (a.action === 'scroll' && a.anim.type !== 'instant' ? 'smart' : types.some(x => x[0] === 'dissolve') && a.anim.type !== 'instant' ? 'dissolve' : 'instant');
      box.appendChild(h('div', {class: 'hdp-sep'}));
      box.appendChild(frow('Animation', pick(types, cur, v => setA(an => { an.type = v; if (v !== 'instant' && !an.dur) an.dur = 300; }, 'Change animation'), 'Animation')));
      if (cur !== 'instant') {
        if (DIRECTED[cur]) { const seg = h('div', {class: 'hd-seg hdp-dir', role: 'radiogroup', 'aria-label': 'Direction'}); for (const d of [['left', 'To the left', 'M10 3L5 8l5 5'], ['right', 'To the right', 'M6 3l5 5-5 5'], ['up', 'Upwards', 'M3 10l5-5 5 5'], ['down', 'Downwards', 'M3 6l5 5 5-5']]) { const b = h('button', {class: 'hd-segb' + (a.anim.dir === d[0] ? ' on' : ''), type: 'button', role: 'radio', 'aria-checked': String(a.anim.dir === d[0]), title: d[1], 'aria-label': d[1], 'data-k': 'dir' + d[0], 'data-v': d[0], disabled: !edit}, arrowIcon(d[2])); b.addEventListener('click', () => setA(an => { an.dir = d[0]; }, 'Change direction')); seg.appendChild(b); } box.appendChild(frow('Direction', seg)); }
        box.appendChild(frow('Easing', pick(EASES, a.anim.ease, v => setA(an => { an.ease = v; }, 'Change easing'), 'Easing')));
        box.appendChild(frow('Duration', numIn(a.anim.dur, v => setA(an => { an.dur = v; }, 'Change duration'), 'Duration in milliseconds', {min: 1, max: 10000, int: true, unit: 'ms'})));
      }
    }
    if (edit) box.appendChild(h('div', {class: 'hdp-edfoot'}, h('button', {class: 'hd-btn hdp-del', type: 'button', 'data-k': 'del', on: {click: () => { const id = me.id, i = me.i; W.sel = null; edClose(); removeReaction(id, i); HD.render.invalidate(); ui.refresh(); }}}, icon('trash'), h('span', {text: 'Remove'}))));
    if (keep) { const el = box.querySelector('[data-k="' + String(keep).replace(/["\\]/g, '') + '"]'); if (el && !el.disabled) { try { el.focus({preventScroll: true}); } catch (e) { /* gone */ } } }
    if (me.pop) me.pop.place();
  }
  function arrowIcon(d) { const NS = 'http://www.w3.org/2000/svg', s = document.createElementNS(NS, 'svg'); s.setAttribute('viewBox', '0 0 16 16'); s.setAttribute('width', 16); s.setAttribute('height', 16); s.setAttribute('fill', 'none'); s.setAttribute('stroke', 'currentColor'); s.setAttribute('stroke-width', '1.4'); s.setAttribute('stroke-linecap', 'round'); s.setAttribute('stroke-linejoin', 'round'); s.setAttribute('aria-hidden', 'true'); s.setAttribute('class', 'hd-ic'); const p = document.createElementNS(NS, 'path'); p.setAttribute('d', d); s.appendChild(p); return s; }

  /* ================================================================ the editor: the Prototype tab */
  const panel = {el: null, sig: '', syncs: [], selKey: ''};
  function summary(a) {
    const t = a.trigger === 'after' ? 'After ' + a.delay + ' ms' : a.trigger === 'key' ? 'Key ' + (a.key ? keyLabel(a.key) : '?') : label(TRIGGERS, a.trigger);
    let what = label(ACTIONS, a.action), missing = false;
    if (NEEDS_TO[a.action]) { if (a.to && N(a.to)) what = (a.action === 'navigate' ? '' : what + ': ') + nameOf(a.to); else { what = what + ' \u2026'; missing = true; } }
    else if (a.action === 'url') { const ok = safeLink(a.url); if (ok) { try { what = 'Open ' + new URL(ok).hostname; } catch (e) { what = 'Open link'; } } else missing = true; }
    return {t: t, what: what, missing: missing};
  }
  function panelSig() {
    const ids = (HD.sel.ids || EMPTY).filter(id => N(id)), page = HD.sel.page, edit = canEdit();
    const fl = flows(page).map(f => f.id + ':' + f.name).join(',');
    if (ids.length !== 1) return ['n' + ids.length, page, edit, P(page, 'device') || 'none', fl, screens(page).length].join('|');
    const id = ids[0], n = N(id), o = overlayConf(id);
    return [id, edit, n.type, n.name, JSON.stringify(n.reactions || null), reactions(id).map(r => { const a = rx(r); return a.to ? nameOf(a.to) : ''; }).join(','), P(id, 'protoStart') === true, P(id, 'flowName') || '', P(id, 'scroll') || 'none', n.fixed === true, isScreen(id), isScreen(n.parent),
      o.pos, o.x, o.y, o.closeOutside, o.dim, W.sel && W.sel.node === id ? W.sel.i : -1, ed && ed.id === id ? ed.i : -1].join('|');
  }
  function colour(get, set, title) {
    const sy = ui.state.syncs, n0 = sy.length, el = ui.colorLine({get: get, set: set, title: title, solidOnly: true, hide: false});
    while (sy.length > n0) panel.syncs.push(sy.pop());
    return el;
  }
  function check(text, on, set) { const cb = h('input', {class: 'hd-cb', type: 'checkbox', checked: !!on, disabled: !canEdit(), 'aria-label': text}); cb.addEventListener('change', () => set(cb.checked)); return h('label', {class: 'hd-check'}, cb, h('span', {text: text})); }
  function renderPanel(el) {
    const sig = panelSig(), selKey = (HD.sel.ids || EMPTY).join(',') + '@' + HD.sel.page;
    if (panel.el === el && el.firstChild && sig === panel.sig) { for (const s of panel.syncs) { try { s(); } catch (e) { /* a stale control */ } } return; }
    const act = document.activeElement;
    if (panel.el === el && el.firstChild && panel.selKey === selKey && act && el.contains(act) && act.tagName === 'INPUT' && act.type !== 'checkbox') return;     /* she is typing: the blur paints */
    panel.el = el; panel.sig = sig; panel.selKey = selKey; panel.syncs = []; clear(el);
    el.classList.add('hdp-panel');
    const ids = (HD.sel.ids || EMPTY).filter(id => N(id)), page = HD.sel.page, edit = canEdit();
    if (ids.length !== 1) { panelPage(el, page, edit, ids.length); return; }
    const id = ids[0], n = N(id), scr = isScreen(id);
    el.appendChild(h('div', {class: 'hd-selhead'}, h('span', {class: 'hd-ltype'}, icon(n.type === 'TEXT' ? 'text' : SCREEN[n.type] ? 'frame' : 'rect', 14)), h('span', {class: 'hd-selname', text: n.name || n.type}), h('span', {class: 'hd-seltype', text: scr ? 'Screen' : 'Layer'})));
    /* flow starting point */
    if (scr) {
      const on = P(id, 'protoStart') === true;
      const s = ui.section(el, 'Flow starting point', [edit ? {icon: on ? 'minus' : 'plus', title: on ? 'Remove the starting point' : 'Start a flow at this frame', run: () => { if (on) setProps(id, {protoStart: null, flowName: null}, 'Remove flow starting point'); else setProps(id, {protoStart: true, flowName: nextFlowName(page)}, 'Add flow starting point'); HD.render.invalidate(); }} : null], {cls: on ? '' : 'bare'});
      if (on) {
        const nm = h('input', {class: 'hd-in', type: 'text', 'aria-label': 'Flow name', maxlength: '60', value: String(P(id, 'flowName') || n.name || 'Flow'), disabled: !edit, spellcheck: 'false'});
        nm.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); nm.blur(); } });
        nm.addEventListener('change', () => { const v = nm.value.trim() || 'Flow'; if (v !== P(id, 'flowName')) setProps(id, {flowName: v}, 'Rename flow'); HD.render.invalidate(); });
        nm.addEventListener('blur', () => ui.refresh());
        const play = h('button', {class: 'hd-ib', type: 'button', title: 'Play this flow', 'aria-label': 'Play this flow', on: {click: () => open(id)}}, icon('play'));
        s.body.appendChild(ui.row(nm, play));
      }
    }
    /* interactions */
    const list = reactions(id);
    const sec = ui.section(el, 'Interactions', [edit ? {icon: 'plus', title: 'Add an interaction', run: () => { const t = scr || !screenOf(id) ? defaultTarget(id) : defaultTarget(id); const i = addReaction(id, t ? {trigger: 'click', action: 'navigate', to: t, anim: {type: 'dissolve', dir: 'left', dur: 300, ease: 'out'}} : {trigger: 'click', action: 'navigate'}); if (i >= 0) { W.sel = {node: id, i: i}; HD.render.invalidate(); renderPanel(el); const row = el.querySelector('.hdp-ix[data-i="' + i + '"] .hdp-ixb'); if (row) edOpen(row, id, i); } }} : null], {cls: list.length ? '' : 'bare'});
    list.forEach((r, i) => {
      const a = rx(r), sm = summary(a), on = (W.sel && W.sel.node === id && W.sel.i === i) || (ed && ed.id === id && ed.i === i);
      const b = h('button', {class: 'hdp-ixb', type: 'button', title: edit ? 'Edit this interaction' : 'See this interaction'}, h('span', {class: 'hdp-ixt', text: sm.t}), h('span', {class: 'hdp-ixarrow', 'aria-hidden': 'true'}, icon('right', 12)), h('span', {class: 'hdp-ixw' + (sm.missing ? ' miss' : ''), text: sm.what}));
      b.addEventListener('click', () => { W.sel = {node: id, i: i}; HD.render.invalidate(); edOpen(b, id, i); ui.refresh(); });
      const rm = h('button', {class: 'hd-ib sm', type: 'button', title: 'Remove', 'aria-label': 'Remove this interaction', disabled: !edit}, icon('minus'));
      rm.addEventListener('click', () => { if (ed && ed.id === id) edClose(); W.sel = null; removeReaction(id, i); HD.render.invalidate(); });
      sec.body.appendChild(h('div', {class: 'hdp-ix' + (on ? ' on' : ''), 'data-i': String(i)}, b, rm));
    });
    if (!list.length && edit) el.appendChild(h('p', {class: 'hd-note pad hdp-tip', text: 'Add an interaction here, or drag the + handle beside the layer onto another frame.'}));
    /* scrolling */
    if (scr) {
      const s2 = ui.section(el, 'Scrolling'); s2.body.appendChild(frow('Overflow', pick(SCROLLS, P(id, 'scroll') || 'none', v => setProps(id, {scroll: v === 'none' ? null : v}, 'Change scrolling'), 'Scroll behaviour')));
      s2.body.appendChild(h('p', {class: 'hd-note', text: 'Layers that reach past the frame scroll into view. A frame taller than the device always scrolls.'}));
    }
    if (!scr && isScreen(n.parent)) { const s3 = ui.section(el, 'Position'); s3.body.appendChild(ui.row(check('Fix position when scrolling', n.fixed === true, v => setProps(id, {fixed: v ? true : null}, v ? 'Fix position' : 'Scroll with the frame')))); }
    /* as an overlay */
    if (scr) {
      const o = overlayConf(id), s4 = ui.section(el, 'When opened as an overlay');
      const setO = (patch, lbl, g) => { const cur = P(id, 'overlay'); setProps(id, {overlay: Object.assign({}, cur && typeof cur === 'object' ? cur : null, patch)}, lbl, g); };
      s4.body.appendChild(frow('Position', pick(OVERLAY_POS, o.pos, v => setO({pos: v}, 'Change overlay position'), 'Overlay position')));
      if (o.pos === 'manual') s4.body.appendChild(h('div', {class: 'hdp-row two'}, h('span', {class: 'hdp-lab', text: 'Offset'}), numIn(o.x, v => setO({x: v}, 'Change overlay position'), 'Overlay X', {key: 'ox'}), numIn(o.y, v => setO({y: v}, 'Change overlay position'), 'Overlay Y', {key: 'oy'})));
      s4.body.appendChild(ui.row(check('Close when clicking outside', o.closeOutside, v => setO({closeOutside: v}, 'Change overlay'))));
      s4.body.appendChild(ui.row(check('Dim the background', o.dim, v => setO({dim: v}, 'Change overlay'))));
      if (o.dim) s4.body.appendChild(colour(() => { const c = overlayConf(id); return {type: 'solid', color: c.dimColor, opacity: c.dimOpacity, visible: true}; }, (p, g) => setO({dimColor: p.color || '#000000', dimOpacity: clamp(num(p.opacity, 1), 0, 1)}, 'Change overlay background', g), 'Overlay background'));
    }
  }
  function panelPage(el, page, edit, count) {
    const pn = N(page) || {};
    refreshShare();
    el.appendChild(h('div', {class: 'hd-selhead'}, h('span', {class: 'hd-ltype'}, icon('page', 14)), h('span', {class: 'hd-selname', text: count > 1 ? count + ' layers' : (pn.name || 'Page')}), h('span', {class: 'hd-seltype', text: count > 1 ? 'Mixed' : 'Prototype'})));
    if (count > 1) { el.appendChild(h('p', {class: 'hd-note pad', text: 'Select one layer to see and edit its interactions.'})); return; }
    const dev = P(page, 'device') || 'none';
    const s = ui.section(el, 'Device');
    s.body.appendChild(frow('Show in', pick(DEVICE_LIST, DEVICES[dev] ? dev : 'none', v => setProps(page, {device: v === 'none' ? null : v}, 'Change device'), 'Device')));
    if (DEVICES[dev]) s.body.appendChild(h('p', {class: 'hd-note', text: 'Screen ' + DEVICES[dev].w + ' \u00D7 ' + DEVICES[dev].h + '. A frame is scaled to the width of the screen; what is taller scrolls.'}));
    const s1 = ui.section(el, 'Background');
    s1.body.appendChild(colour(() => { const c = P(page, 'deviceBg'); return {type: 'solid', color: typeof c === 'string' ? c : cssVar('--stage', '#17161F').toUpperCase(), opacity: 1, visible: true}; }, (p, g) => setProps(page, {deviceBg: p.color || '#17161F'}, 'Change prototype background', g), 'Prototype background'));
    const fl = flows(page), s2 = ui.section(el, 'Flows', null, {cls: fl.length ? '' : 'bare'});
    for (const f of fl) {
      const b = h('button', {class: 'hdp-flowrow', type: 'button', title: 'Select this frame'}, icon('play', 14), h('span', {text: f.name}), h('span', {class: 'hdp-flowframe', text: nameOf(f.id)}));
      b.addEventListener('click', () => { HD.sel.set([f.id]); });
      const play = h('button', {class: 'hd-ib sm', type: 'button', title: 'Play this flow', 'aria-label': 'Play ' + f.name, on: {click: () => open(f.id)}}, icon('play'));
      s2.body.appendChild(h('div', {class: 'hdp-ix'}, b, play));
    }
    const has = screens(page).length > 0;
    el.appendChild(h('p', {class: 'hd-note pad hdp-tip', text: !has ? 'Draw a frame first. Each frame is one screen of the prototype.' : fl.length ? 'Select a layer to add an interaction, or drag its + handle onto another frame.' : 'Select a frame and add a flow starting point. Select any layer to add an interaction, or drag its + handle onto another frame.'}));
    const acts = h('div', {class: 'hdp-acts'},
      h('button', {class: 'hd-btn pri', type: 'button', disabled: !has, on: {click: () => open(null)}}, icon('play'), h('span', {text: 'Present'})),
      h('button', {class: 'hd-btn', type: 'button', disabled: !has, on: {click: () => { const f = flows(page)[0], t = f ? f.id : screens(page)[0]; if (t) copyLink(t); }}}, icon('link'), h('span', {text: 'Copy prototype link'})));
    el.appendChild(acts);
  }
  ui.registerPanel('right', 'prototype', {title: 'Prototype', render: renderPanel});

  /* ---------------------------------------------------------------- commands + menu */
  ui.command({id: 'proto-link', label: 'Copy prototype link', group: 'Other', run: () => { const page = HD.sel.page, s = (HD.sel.ids || EMPTY).map(screenOf).find(Boolean) || (flows(page)[0] || {}).id || screens(page)[0]; if (s) copyLink(s); else ui.toast('Draw a frame first: a prototype plays frames.'); }});
  ui.command({id: 'proto-flow', label: 'Add or remove a flow starting point', group: 'Other', edit: true, when: () => (HD.sel.ids || EMPTY).some(isScreen), run: () => { const id = HD.sel.ids.find(isScreen); if (!id) return; if (P(id, 'protoStart') === true) setProps(id, {protoStart: null, flowName: null}, 'Remove flow starting point'); else setProps(id, {protoStart: true, flowName: nextFlowName(st().pageOf(id))}, 'Add flow starting point'); HD.render.invalidate(); }});
  ui.registerMenu('context', ids => { const id = ids.length === 1 && isScreen(ids[0]) ? ids[0] : null; return id ? {label: 'Present from this frame', icon: 'play', run: () => open(id)} : null; });

  /* ---------------------------------------------------------------- staying in step with the document */
  function onDoc() {
    docVer++; W.conns = null;
    if (ed) { const act = document.activeElement; if (!(act && ed.box.contains(act) && act.tagName === 'INPUT')) edRender(); }
    if (W.sel && (!N(W.sel.node) || !reactions(W.sel.node)[W.sel.i])) W.sel = null;
    if (Pl.open) { Pl.stale = true; if (vclock === null) wake(); }
  }
  st().on('change', onDoc); st().on('load', () => { W.sel = null; edClose(); onDoc(); });
  HD.sel.on('change', () => { if (W.sel && !(HD.sel.ids.length === 1 && HD.sel.ids[0] === W.sel.node)) { W.sel = null; } if (ed && !(HD.sel.ids.length === 1 && HD.sel.ids[0] === ed.id)) edClose(); });
  setTimeout(() => { if (HD.app && HD.app.on) HD.app.on('close', () => { close(true); shareInfo.file = null; shareInfo.token = null; }); }, 0);
  if (window.HoolaTheme && window.HoolaTheme.onChange) window.HoolaTheme.onChange(() => { if (Pl.open) { Pl.stale = true; wake(); } });

  /* ================================================================ public */
  HD.proto = {
    open: open, close: () => close(), link: link, screens: screens, flows: flows, isScreen: isScreen, reactions: id => reactions(id).map(rx), wires: wires, handle: handle, badges: () => badgeBoxes.slice(),
    get isOpen() { return Pl.open; },
    /* what the player shows right now (read only) */
    state() {
      if (!Pl.open) return {open: false};
      const L = Pl.L, a = Pl.anim;
      return {open: true, frame: Pl.base ? Pl.base.id : null, start: Pl.start, page: Pl.page, zoom: Pl.zoom, scroll: Pl.base ? {x: Pl.base.sx, y: Pl.base.sy, maxX: Pl.base.maxX, maxY: Pl.base.maxY} : null,
        overlays: Pl.overlays.map(o => ({id: o.surf.id, x: o.x, y: o.y, scroll: {x: o.surf.sx, y: o.surf.sy}})), history: Pl.history.map(x => x.frame), anim: a ? {kind: a.kind, type: a.type, p: a.p} : null,
        smart: a && a.kind === 'smart' ? Pl.probe.map(x => Object.assign({}, x)) : [], timers: Pl.timers.length, hints: Pl.hints ? Pl.hints.rects.length : 0, ask: !!Pl.ask, device: L ? L.devKey : 'none',
        layout: L ? {x: L.x, y: L.y, w: L.w, h: L.h, k: L.k, vw: L.vw, vh: L.vh} : null, scratch: scratch.keep.size + scratch.temp.size};
    },
    /* the middle of a node on the page, in client pixels (null when it is not on screen) */
    pointOf(id) {
      if (!Pl.open) return null;
      const surfs = Pl.overlays.map(o => o.surf).reverse().concat([Pl.base]);
      for (const s of surfs) { const r = s && cssRect(s, id); if (r) { const cr = Pl.canvas.getBoundingClientRect(); return [cr.left + r.x + r.w / 2, cr.top + r.y + r.h / 2]; } }
      return null;
    },
    clock: {
      freeze() { if (vclock === null) vclock = performance.now(); if (Pl.raf) { cancelAnimationFrame(Pl.raf); Pl.raf = 0; } clearTimeout(Pl.timerT); Pl.timerT = 0; return vclock; },
      step(ms) { if (vclock === null) vclock = performance.now(); vclock += Math.max(0, +ms || 0); frame(); return vclock; },
      release() { if (vclock === null) return; const d = performance.now() - vclock; vclock = null; if (Pl.anim) Pl.anim.t0 += d; if (Pl.glide) Pl.glide.t0 += d; if (Pl.hints) Pl.hints.t0 += d; for (const t of Pl.timers) t.at += d; scheduleTimers(); wake(); }
    }
  };
})();

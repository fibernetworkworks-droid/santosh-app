/* HOOLA DESIGN - D3 systems (docs/HOOLA_DESIGN_PLAN.md phase D3): components, instances + overrides, variants,
   component properties, styles, variables + modes, the Assets panel and the library across files.  ->  HD.comp

   Everything here is an ordinary op through HD.store.tx: multiplayer and undo come for free, nothing is mutated in place.

   INSTANCES. An INSTANCE has `comp` (the COMPONENT's id) and no child nodes; the renderer draws the component's
   subtree with the overrides in `ov`. This file resolves the SAME tree for the editor (HD.comp.vtree): a virtual
   node = {id, path, n (resolved props), kids, world (matrix), isRoot (a nested instance), comp}.
     path            child ids inside the component joined by "/" ("" = the instance itself). Through a nested
                     instance the path goes on with the ids inside ITS component: "<nested instance id>/<child id>".
     overrides       of a child: inst.ov["<path>"] = {prop: value}.  Of the instance's own look (fills, strokes,
                     radius, effects, opacity ...): the property written on the INSTANCE node itself; without it the
                     component's value shows (HD.store.prop is taught that fallback here, so the first-wave panel
                     shows what is drawn). x, y, w, h, rot, name ... always belong to the instance.
     deep select     double-click (or Ctrl / Cmd + click) inside a selected instance = HD.comp.sub {inst, path}; the
                     Design panel then edits that virtual layer and every edit is ONE tx that writes `ov`.
   `ov` is one property, so two people overriding two children of the SAME instance at the same moment: the later
   write wins (last writer wins per property, the rule of the whole document).

   DELETING A COMPONENT detaches its instances first, in the same undo step (HD.store.remove is wrapped): they become
   plain frames with real layers, so nothing is left pointing at a deleted component.

   VARIANTS. A COMPONENT_SET holds components named "Prop=Value, Prop2=Value". An instance of one of them shows a
   control per property and swaps `comp` to the matching variant (overrides are kept by layer name).
   COMPONENT PROPERTIES. comp.cprops = [{id, name, type: "text"|"bool"|"swap", target: "<child path>", def}]; the
   instance shows one field per entry, which writes ov[target].chars / .visible / .comp.

   STYLES live on the root node: styles = {sid: {kind: "fill"|"text"|"effect", name, value}}. A node links with
   fillStyle / textStyle / effectStyle AND carries the resolved value. Editing a style rewrites every linked node in
   one tx; changing a linked value by hand drops the link in the same tx (the renderer would otherwise keep drawing
   the style).

   VARIABLES live on the root node: vars = {vid: {name, type: "color"|"number"|"string"|"bool", modes: {mode: value}}},
   modes = [names]. A frame can carry `mode`; a node resolves through the nearest ancestor that has one (else the
   first mode). A binding is node.bind = {"$<prop>": vid} with <prop> one of fill w h gap padding radius opacity chars
   visible, and the RESOLVED value is written into the node. The "$" keeps the renderer's own draw-time lookup (which
   only knows the first mode) out of it: what is in the node is what is drawn. Bound values are written again, in one
   tx, when a variable or a frame's mode changes - only on the client that made the change.

   Loaded after hd-ui.js. Plain browser JS, no dependencies, no eval; every text from the document is textContent. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const S = HD.store, M = HD.math, UI = HD.ui, T = HD.tools;
  if (!S || !M || !UI || !T) return;
  const h = UI.h, icon = UI.icon, clear = UI.clear;
  const ROOT = S.ROOT, EPS = 0.01, VIOLET = '#8B3DFF';
  const U = () => T.u, A = () => T.act;

  /* ---------------------------------------------------------------- small helpers */
  function num(v, d) { return typeof v === 'number' && v === v && v !== Infinity && v !== -Infinity ? v : d; }
  function clone(v) { return v === undefined ? undefined : JSON.parse(JSON.stringify(v)); }
  function same(a, b) { return a === b || (a !== undefined && b !== undefined && JSON.stringify(a) === JSON.stringify(b)); }
  function r2(v) { return Math.round(v * 100) / 100; }
  function typeOf(id) { const n = S.get(id); return n ? n.type : ''; }
  function rootNode() { return S.get(ROOT) || {}; }
  function canEdit() { return U().canEdit(); }
  function guard() { if (!canEdit()) { UI.toast('This file is view only.'); return false; } return true; }
  function write(label, fn, g) { if (!canEdit()) return undefined; if (g) { g.apply(fn); return undefined; } return S.tx(label, fn); }
  function W(n) { return num(n.w, 100); }
  function H(n) { return n.type === 'LINE' ? 0 : num(n.h, 100); }
  function nextSibling(id) { const sib = S.children(S.parent(id)), i = sib.indexOf(id); return i >= 0 && i + 1 < sib.length ? sib[i + 1] : null; }
  function selIds() { return U().selIds(); }
  function tops() { return U().topLevel(selIds()); }
  const DEFS = {};
  function defOf(type, name) { let d = DEFS[type]; if (!d) d = DEFS[type] = S.defaults(type) || {}; return d[name]; }
  function val(n, name) { const v = n[name]; return v === undefined ? defOf(n.type, name) : v; }
  function hash(str) { let x = 0x811c9dc5; for (let i = 0; i < str.length; i++) { x ^= str.charCodeAt(i); x = Math.imul(x, 0x01000193); } return ('0000000' + (x >>> 0).toString(16)).slice(-8); }
  function newKey(prefix) { return prefix + String(S.newId()).replace(':', '_'); }
  function hasAncestorOfType(id, types) { let c = S.parent(id), g = 0; while (c && g++ < 2000) { if (types[typeOf(c)]) return c; c = S.parent(c); } return null; }
  let ver = 1, rootVer = 1;                     /* bumped on every document change / on a change of the root node */

  /* ---------------------------------------------------------------- what belongs to an instance, what can be overridden on it */
  const ROOT_OV = {fills: 'Fill', strokes: 'Stroke', strokeWeight: 'Stroke weight', strokeAlign: 'Stroke position', strokeCap: 'Line ends', strokeJoin: 'Line joins',
    dash: 'Dashes', radius: 'Corner radius', effects: 'Effects', opacity: 'Opacity', blend: 'Blend mode', clip: 'Clip content', fillStyle: 'Fill style', effectStyle: 'Effect style'};
  const PROP_LABEL = Object.assign({chars: 'Text', visible: 'Visibility', comp: 'Swapped component', fontSize: 'Font size', fontWeight: 'Font weight', font: 'Font', x: 'X', y: 'Y', w: 'Width', h: 'Height',
    align: 'Text align', lineHeight: 'Line height', letterSpacing: 'Letter spacing', textStyle: 'Text style', italic: 'Italic', ov: 'Nested changes'}, ROOT_OV);
  const origProp = S.prop;
  /* an instance shows its component's look until it has its own: the same rule the renderer draws by */
  S.prop = function (id, name) {
    const n = S.get(id);
    if (n !== undefined && n.type === 'INSTANCE' && n[name] === undefined && ROOT_OV[name] !== undefined && n.comp) {
      const c = S.get(n.comp);
      if (c !== undefined && c[name] !== undefined) return c[name];
    }
    return origProp.call(S, id, name);
  };

  /* ---------------------------------------------------------------- the virtual tree of an instance (mirrors hd-render.js instRoot / vNode) */
  const CONT = {FRAME: 1, GROUP: 1, SECTION: 1, COMPONENT: 1, COMPONENT_SET: 1, INSTANCE: 1};
  function ovOf(n) { return n && n.ov && typeof n.ov === 'object' ? n.ov : {}; }
  function vRoot(inst, ovs, depth, seen, at) {
    const comp = inst.comp ? S.get(inst.comp) : null;
    const v = {id: at.id, key: at.key, path: at.path, n: inst, instN: inst, kids: [], sx: 1, sy: 1, cw: 0, ch: 0, world: null, parent: at.parent, isRoot: true, inst: true, comp: inst.comp || '', missing: !comp};
    if (!comp || depth > 6 || seen.has(inst.comp)) return v;
    const rootN = Object.assign({}, comp, inst);
    rootN.type = 'INSTANCE';
    if (inst.w === undefined) rootN.w = comp.w;
    if (inst.h === undefined) rootN.h = comp.h;
    const all = [{ov: ovOf(inst), path: ''}].concat(ovs);
    for (const e of all) { const o = e.path === '' ? e.ov[''] : undefined; if (o && typeof o === 'object') Object.assign(rootN, o); }
    v.n = rootN;
    v.cw = W(comp); v.ch = H(comp);
    v.sx = v.cw > EPS ? W(rootN) / v.cw : 1; v.sy = v.ch > EPS ? H(rootN) / v.ch : 1;
    const seen2 = new Set(seen); seen2.add(inst.comp);
    const ks = S.children(inst.comp);
    for (let i = 0; i < ks.length; i++) { const k = vKid(ks[i], all, depth, seen2, v); if (k) v.kids.push(k); }
    return v;
  }
  function vKid(cid, ovs, depth, seen, par) {
    const c = S.get(cid);
    if (!c) return null;
    const ovs2 = []; let n = c;
    for (let i = 0; i < ovs.length; i++) {
      const e = ovs[i], p = e.path ? e.path + '/' + cid : cid, o = e.ov[p];
      ovs2.push({ov: e.ov, path: p});
      if (o && typeof o === 'object') { if (n === c) n = Object.assign({}, c); Object.assign(n, o); }
    }
    const path = par.path ? par.path + '/' + cid : cid, key = par.key + '/' + cid;
    if (n.type === 'INSTANCE') return vRoot(n, ovs2, depth + 1, seen, {id: cid, key: key, path: path, parent: par});
    const v = {id: cid, key: key, path: path, n: n, kids: [], sx: 1, sy: 1, world: null, parent: par, isRoot: false, comp: '', missing: false};
    if (CONT[n.type] === 1) { const ks = S.children(cid); for (let i = 0; i < ks.length; i++) { const k = vKid(ks[i], ovs2, depth, seen, v); if (k) v.kids.push(k); } }
    return v;
  }
  /* an instance at another size than its component: laid out again when the component has auto layout or its children
     carry constraints (HD.layout.virtual, as the renderer does), else simply scaled */
  function vFit(v, depth) {
    if (v.inst === true && depth < 8) {
      v.sx = v.cw > EPS ? W(v.n) / v.cw : 1; v.sy = v.ch > EPS ? H(v.n) / v.ch : 1;
      if ((Math.abs(v.sx - 1) > 1e-6 || Math.abs(v.sy - 1) > 1e-6) && v.kids.length && HD.layout && typeof HD.layout.virtual === 'function') {
        const l = v.n.layout; let wants = !!(l && (l.mode === 'h' || l.mode === 'v'));
        for (let i = 0; i < v.kids.length && !wants; i++) { const c = v.kids[i].n.cons; if (c !== undefined && c !== null) wants = true; }
        let ok = false; if (wants) { try { ok = HD.layout.virtual(v, v.cw, v.ch); } catch (e) { ok = false; } }
        if (ok) { v.sx = 1; v.sy = 1; }
      }
    }
    for (let i = 0; i < v.kids.length; i++) vFit(v.kids[i], v.kids[i].inst === true ? depth + 1 : depth);
  }
  function vPlace(v) {
    for (let i = 0; i < v.kids.length; i++) {
      const k = v.kids[i], n = k.n, lm = M.nodeMatrix(num(n.x, 0), num(n.y, 0), W(n), H(n), num(n.rot, 0), n.flipH === true, n.flipV === true), sx = v.sx, sy = v.sy;
      k.world = M.mul(v.world, sx === 1 && sy === 1 ? lm : [lm[0] * sx, lm[1] * sy, lm[2] * sx, lm[3] * sy, lm[4] * sx, lm[5] * sy]);
      vPlace(k);
    }
  }
  const treeCache = new Map();
  function buildTree(instId, node) { const t = vRoot(node, [], 0, new Set(), {id: instId, key: instId, path: '', parent: null}); vFit(t, 0); t.world = S.worldMatrix(instId); vPlace(t); return t; }
  /* the resolved tree of an instance, or null when the id is not an instance */
  function vtree(instId) {
    const inst = S.get(instId);
    if (!inst || inst.type !== 'INSTANCE') return null;
    const c = treeCache.get(instId);
    if (c && c.ver === ver) return c.tree;
    const tree = buildTree(instId, inst);
    if (treeCache.size > 200) treeCache.clear();
    treeCache.set(instId, {ver: ver, tree: tree});
    return tree;
  }
  function vfind(tree, path) {
    if (!tree) return null;
    if (!path) return tree;
    const segs = String(path).split('/'); let v = tree;
    for (let i = 0; i < segs.length; i++) { let next = null; for (let j = 0; j < v.kids.length; j++) if (v.kids[j].id === segs[i]) { next = v.kids[j]; break; } if (!next) return null; v = next; }
    return v;
  }
  function vnode(instId, path) { return vfind(vtree(instId), path); }
  function vwalk(v, fn, depth) { depth = depth || 0; if (fn(v, depth) === false) return; for (let i = 0; i < v.kids.length; i++) vwalk(v.kids[i], fn, depth + 1); }
  function vcorners(v) { const w = W(v.n), hh = H(v.n), m = v.world; return [M.apply(m, 0, 0), M.apply(m, w, 0), M.apply(m, w, hh), M.apply(m, 0, hh)]; }
  function anyVisible(list) { if (!Array.isArray(list)) return false; for (let i = 0; i < list.length; i++) { const p = list[i]; if (p && p.visible !== false && (p.opacity === undefined || p.opacity > 0)) return true; } return false; }
  function vhit(v, wx, wy, tol, out) {
    if (v.n.visible === false) return false;
    const p = M.apply(M.inv(v.world), wx, wy), w = W(v.n), hh = H(v.n);
    const inBox = p[0] >= -tol && p[1] >= -tol && p[0] <= w + tol && p[1] <= hh + tol;
    const cont = CONT[v.n.type] === 1;
    if (cont && val(v.n, 'clip') === true && !inBox) return false;
    for (let i = v.kids.length - 1; i >= 0; i--) { if (vhit(v.kids[i], wx, wy, tol, out)) { out.unshift(v); return true; } }
    if (!inBox) return false;
    if (cont && v.n.type !== 'INSTANCE' && !anyVisible(v.n.fills) && !anyVisible(v.n.strokes)) return false;
    out.unshift(v);
    return true;
  }
  /* the virtual layers under a world point, outermost first (without the instance itself) */
  function hitChain(instId, wx, wy) {
    const tree = vtree(instId), out = [];
    if (!tree) return out;
    vhit(tree, wx, wy, 3 / ((HD.render.view && HD.render.view.zoom) || 1), out);
    return out.slice(1);
  }

  /* ---------------------------------------------------------------- overrides */
  function isOverridden(instId, path, prop) {
    const n = S.get(instId); if (!n) return false;
    if (!path) return prop === undefined ? Object.keys(ROOT_OV).some(k => n[k] !== undefined) : (ROOT_OV[prop] !== undefined && n[prop] !== undefined);
    const o = ovOf(n)[path]; if (!o) return false;
    return prop === undefined ? Object.keys(o).length > 0 : o[prop] !== undefined;
  }
  /* the value a property of a virtual layer would have WITHOUT this instance's own override of it */
  function baseValue(instId, path, prop) {
    const inst = S.get(instId); if (!inst) return undefined;
    if (!path) { const c = inst.comp ? S.get(inst.comp) : null; return c ? val(Object.assign({}, c, {type: 'INSTANCE'}), prop) : defOf('INSTANCE', prop); }
    const ov = Object.assign({}, ovOf(inst));
    if (ov[path]) { const e = Object.assign({}, ov[path]); delete e[prop]; ov[path] = e; }
    const v = vfind(buildTree(instId, Object.assign({}, inst, {ov: ov})), path);
    return v ? val(v.n, prop) : undefined;
  }
  const LINK_OF = {fills: 'fillStyle', effects: 'effectStyle'};
  const TEXT_KEYS = ['font', 'fontSize', 'fontWeight', 'italic', 'lineHeight', 'letterSpacing', 'decoration', 'textCase'];
  /* write (value) or take back (undefined) overrides of one virtual layer; ONE tx. path "" = the instance itself. */
  function setOverride(instId, path, patch, label, g) {
    return write(label || 'Change in instance', () => {
      const inst = S.get(instId); if (!inst || inst.type !== 'INSTANCE') return false;
      if (!path) { const p = {}; for (const k in patch) p[k] = patch[k] === undefined ? null : patch[k]; return S.set(instId, p); }
      const ov = Object.assign({}, ovOf(inst)), cur = Object.assign({}, ov[path] || {}), v = vfind(buildTree(instId, inst), path);
      for (const k in patch) {
        if (patch[k] === undefined) { delete cur[k]; continue; }
        cur[k] = patch[k];
        /* a style link on the layer would keep drawing the style: an override of the value switches the link off here */
        if (v && LINK_OF[k] && patch[LINK_OF[k]] === undefined && v.n[LINK_OF[k]]) cur[LINK_OF[k]] = '';
        if (v && TEXT_KEYS.indexOf(k) >= 0 && patch.textStyle === undefined && v.n.textStyle) cur.textStyle = '';
      }
      ov[path] = cur;
      const probe = Object.assign({}, inst, {ov: ov});
      for (const k in cur) {                                  /* back at the component's own value = no override */
        const o2 = Object.assign({}, ov), e2 = Object.assign({}, cur); delete e2[k]; o2[path] = e2; probe.ov = o2;
        const bv = vfind(buildTree(instId, probe), path);
        if (bv && same(val(bv.n, k), cur[k]) && !(k === 'comp')) delete cur[k];
      }
      if (Object.keys(cur).length) ov[path] = cur; else delete ov[path];
      return S.set(instId, {ov: Object.keys(ov).length ? ov : null});
    }, g);
  }
  function resetOverride(instId, path, prop) {
    return write('Reset override', () => {
      const inst = S.get(instId); if (!inst) return false;
      if (!path) { const p = {}; if (prop) p[prop] = null; else for (const k in ROOT_OV) if (inst[k] !== undefined) p[k] = null; return S.set(instId, p); }
      const ov = Object.assign({}, ovOf(inst));
      if (prop === undefined) { for (const k in ov) if (k === path || k.indexOf(path + '/') === 0) delete ov[k]; }
      else if (ov[path]) { const e = Object.assign({}, ov[path]); delete e[prop]; if (prop === 'comp') for (const k in ov) if (k.indexOf(path + '/') === 0) delete ov[k];
        if (Object.keys(e).length) ov[path] = e; else delete ov[path]; }
      return S.set(instId, {ov: Object.keys(ov).length ? ov : null});
    });
  }
  function resetAll(ids) {
    ids = [].concat(ids).filter(id => typeOf(id) === 'INSTANCE'); if (!ids.length || !guard()) return;
    S.tx('Reset all changes', () => { for (const id of ids) { const n = S.get(id), p = {ov: null}; for (const k in ROOT_OV) if (n[k] !== undefined) p[k] = null; S.set(id, p); } });
  }
  /* every change an instance carries: [{path, prop, layer, label}] */
  function listOverrides(instId) {
    const n = S.get(instId), out = []; if (!n || n.type !== 'INSTANCE') return out;
    for (const k in ROOT_OV) if (n[k] !== undefined) out.push({path: '', prop: k, layer: '', label: ROOT_OV[k]});
    const ov = ovOf(n), tree = vtree(instId);
    for (const path in ov) { if (!path) continue; const v = vfind(tree, path); if (!v) continue;
      for (const k in ov[path]) { if ((k === 'fillStyle' || k === 'effectStyle' || k === 'textStyle') && !ov[path][k]) continue; out.push({path: path, prop: k, layer: v.n.name || v.n.type, label: PROP_LABEL[k] || k}); } }
    return out;
  }

  /* ---------------------------------------------------------------- components + instances */
  function isMain(id) { return typeOf(id) === 'COMPONENT'; }
  function inSet(id) { return typeOf(S.parent(id)) === 'COMPONENT_SET'; }
  function standalone(id) { return isMain(id) && !inSet(id); }
  function mainOf(instId) { const n = S.get(instId); return n && n.comp && S.has(n.comp) ? n.comp : null; }
  function compName(id) { const n = S.get(id); if (!n) return 'Missing component'; if (inSet(id)) { const s = S.get(n.parent); return (s && s.name) || n.name || 'Component'; } return n.name || 'Component'; }
  /* every component of the file: [{id, set (id | null), name}] sets first by name; a set lists its variants in `variants` */
  function listComponents() {
    const out = [];
    S.walk(ROOT, (id, n) => {
      if (n.type === 'COMPONENT_SET') { const vs = S.children(id).filter(isMain); if (vs.length) out.push({id: id, kind: 'set', name: n.name || 'Component set', variants: vs, first: vs[0]}); return false; }
      if (n.type === 'COMPONENT') { out.push({id: id, kind: 'component', name: n.name || 'Component', variants: [id], first: id}); return false; }
      if (n.type === 'INSTANCE') return false;
      return undefined;
    });
    return out.sort((a, b) => a.name.toLowerCase() < b.name.toLowerCase() ? -1 : a.name.toLowerCase() > b.name.toLowerCase() ? 1 : 0);
  }
  function instancesOf(compIds) {
    const set = compIds instanceof Set ? compIds : new Set([].concat(compIds)), out = [];
    S.walk(ROOT, (id, n) => { if (n.type === 'INSTANCE') { if (set.has(n.comp)) out.push(id); return false; } return undefined; });
    return out;
  }
  function boxInParent(ids, parent) {
    const inv = M.inv(U().wm(parent)); let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const id of ids) for (const p of U().corners(id)) { const q = M.apply(inv, p[0], p[1]); x0 = Math.min(x0, q[0]); y0 = Math.min(y0, q[1]); x1 = Math.max(x1, q[0]); y1 = Math.max(y1, q[1]); }
    return {x: x0, y: y0, w: x1 - x0, h: y1 - y0};
  }
  /* the selection becomes a component: a frame or a group turns into one, anything else is wrapped in one */
  function createComponent() {
    if (!guard()) return [];
    const ids = tops(); if (!ids.length) { UI.toast('Select the layers that should become a component.'); return []; }
    for (const id of ids) {
      const t = typeOf(id); let bad = '';
      if (t === 'COMPONENT' || t === 'COMPONENT_SET') bad = 'That is already a component.';
      else if (hasAncestorOfType(id, {COMPONENT: 1, COMPONENT_SET: 1})) bad = 'A component can not sit inside another component. Use an instance instead.';
      else { S.walk(id, (k, n) => { if (n.type === 'COMPONENT' || n.type === 'COMPONENT_SET') bad = 'The selection already holds a component.'; }); }
      if (bad) { UI.toast(bad); return []; }
    }
    const out = [], each = ids.every(id => typeOf(id) === 'FRAME' || typeOf(id) === 'GROUP');
    S.tx('Create component', () => {
      if (each) { for (const id of ids) { S.set(id, typeOf(id) === 'GROUP' ? {type: 'COMPONENT', clip: false} : {type: 'COMPONENT'}); out.push(id); } return; }
      const last = ids[ids.length - 1], parent = S.parent(last), before = nextSibling(last), b = boxInParent(ids, parent);
      const id = S.create('COMPONENT', parent, {name: ids.length === 1 ? ((S.get(ids[0]) || {}).name || 'Component') : U().nextName('COMPONENT'), x: r2(b.x), y: r2(b.y), w: Math.max(1, r2(b.w)), h: Math.max(1, r2(b.h)), fills: [], clip: false}, before || undefined);
      S.move(ids, id, null);
      out.push(id);
    });
    HD.sel.set(out);
    return out;
  }
  /* a new instance of a component: `comp` + its own place and size, no child nodes */
  function createInstance(compId, parentId, x, y, before) {
    const c = S.get(compId);
    if (!c || c.type !== 'COMPONENT' || !S.has(parentId)) return null;
    if (parentId === compId || S.isAncestor(compId, parentId)) { UI.toast('A component can not hold an instance of itself.'); return null; }
    const p = {name: compName(compId), comp: compId, x: r2(num(x, 0)), y: r2(num(y, 0)), w: W(c), h: H(c)};
    if (c.rot) p.rot = 0; if (c.flipH) p.flipH = false; if (c.flipV) p.flipV = false; if (c.visible === false) p.visible = true;
    return S.create('INSTANCE', parentId, p, before || undefined);
  }
  /* an instance at a world point (the Assets panel drops here); centred on the point */
  function insertAt(compId, wx, wy) {
    if (!guard()) return null;
    const c = S.get(compId); if (!c) return null;
    let parent = U().containerAt(wx, wy);
    if (parent === compId || S.isAncestor(compId, parent) || typeOf(parent) === 'COMPONENT_SET') parent = HD.sel.page;
    const p = M.apply(M.inv(U().wm(parent)), wx, wy); let id = null;
    S.tx('Insert instance', () => { id = createInstance(compId, parent, Math.round(p[0] - W(c) / 2), Math.round(p[1] - H(c) / 2)); });
    if (id) HD.sel.set([id]);
    return id;
  }
  function goToMain(instId) {
    const c = mainOf(instId); if (!c) { UI.toast('The main component of this instance is not in the file any more.'); return; }
    const pg = S.pageOf(c); if (pg && pg !== HD.sel.page) UI.setPage(pg);
    HD.sel.set([c]); T.view.fit([c]); UI.revealLayers([c]);
  }

  /* ---- detach: the instance becomes a frame with real layers, overrides applied, fresh ids */
  const NOT_COPIED = {parent: 1, idx: 1, type: 1};
  function scaled(n, sx, sy) {
    if (Math.abs(sx - 1) < 1e-6 && Math.abs(sy - 1) < 1e-6) return n;
    const s = (sx + sy) / 2, o = Object.assign({}, n), mul = (k, f) => { if (typeof o[k] === 'number') o[k] = r2(o[k] * f); };
    mul('x', sx); mul('y', sy); mul('w', sx); mul('h', sy); mul('fontSize', s); mul('strokeWeight', s); mul('letterSpacing', s); mul('lineHeight', s);
    if (typeof o.radius === 'number') o.radius = r2(o.radius * s); else if (Array.isArray(o.radius)) o.radius = o.radius.map(v => r2(num(v, 0) * s));
    if (Array.isArray(o.effects)) o.effects = o.effects.map(e => { const f = Object.assign({}, e); for (const k of ['x', 'y', 'blur', 'spread']) if (typeof f[k] === 'number') f[k] = r2(f[k] * s); return f; });
    if (o.layout && typeof o.layout === 'object') { const l = Object.assign({}, o.layout); if (typeof l.gap === 'number') l.gap = r2(l.gap * s); if (Array.isArray(l.pad)) l.pad = l.pad.map(v => r2(num(v, 0) * s)); o.layout = l; }
    if (o.type === 'VECTOR' && typeof o.path === 'string' && o.path) o.path = U().scalePath(o.path, sx, sy);
    return o;
  }
  function cleanProps(n) { const p = {}; for (const k in n) if (!NOT_COPIED[k] && n[k] !== undefined && n[k] !== null) p[k] = n[k]; return p; }
  function materialise(v, parentId, topOv, sx, sy, map) {
    let id;
    if (v.isRoot) {                                           /* a nested instance stays an instance and keeps what was changed inside it */
      const p = cleanProps(scaled(v.instN, sx, sy)), ov = Object.assign({}, ovOf(v.instN)), pre = v.path + '/';
      if (p.w === undefined) p.w = r2(W(v.n) * sx); if (p.h === undefined) p.h = r2(H(v.n) * sy);
      for (const k in topOv) if (k.indexOf(pre) === 0) ov[k.slice(pre.length)] = Object.assign({}, ov[k.slice(pre.length)] || {}, topOv[k]);
      delete p.ov; if (Object.keys(ov).length) p.ov = ov;
      id = S.create('INSTANCE', parentId, p);
      map[v.id] = id;
      return id;
    }
    id = S.create(v.n.type, parentId, cleanProps(scaled(v.n, sx, sy)));
    map[v.id] = id;
    for (let i = 0; i < v.kids.length; i++) materialise(v.kids[i], id, topOv, sx, sy, map);
    return id;
  }
  /* after a REAL instance inside a component was detached: overrides other instances hold for its layers follow the new ids */
  function rekeyAfterDetach(niId, map) {
    if (!hasAncestorOfType(niId, {COMPONENT: 1})) return;
    S.walk(ROOT, (id, n) => {
      if (n.type !== 'INSTANCE') return undefined;
      const ov = ovOf(n); let next = null;
      for (const k in ov) {
        const segs = k.split('/'), i = segs.indexOf(niId); if (i < 0 || i === segs.length - 1) continue;
        let hit = false; for (let j = i + 1; j < segs.length && map[segs[j]]; j++) { segs[j] = map[segs[j]]; hit = true; }
        if (!hit) continue;
        if (!next) next = Object.assign({}, ov);
        delete next[k]; next[segs.join('/')] = ov[k];
      }
      if (next) S.set(id, {ov: next});
      return false;
    });
  }
  function detachOne(instId) {
    const inst = S.get(instId); if (!inst || inst.type !== 'INSTANCE') return false;
    const tree = buildTree(instId, inst), topOv = ovOf(inst), p = {type: 'FRAME', comp: null, ov: null}, skip = {type: 1, parent: 1, idx: 1, name: 1, x: 1, y: 1, comp: 1, ov: 1, cprops: 1, desc: 1, libSrc: 1, libHash: 1, libId: 1, protoStart: 1};
    for (const k in tree.n) if (!skip[k] && tree.n[k] !== undefined && !same(tree.n[k], inst[k])) p[k] = tree.n[k];
    if (p.layout && (Math.abs(tree.sx - 1) > 1e-6 || Math.abs(tree.sy - 1) > 1e-6)) p.layout = scaled({layout: p.layout}, tree.sx, tree.sy).layout;
    S.set(instId, p);
    const map = {};
    for (let i = 0; i < tree.kids.length; i++) materialise(tree.kids[i], instId, topOv, tree.sx, tree.sy, map);
    rekeyAfterDetach(instId, map);
    return true;
  }
  function detach(ids) {
    ids = [].concat(ids || selIds()).filter(id => typeOf(id) === 'INSTANCE'); if (!ids.length || !guard()) return [];
    S.tx('Detach instance', () => { for (const id of ids) detachOne(id); });
    clearSub(); HD.sel.set(ids);
    return ids;
  }

  /* ---- swap: another component, the overrides whose layers still match (by name and type) stay */
  function nameIndex(compId) {
    const byPath = new Map(), byKey = new Map();
    const walk = (pid, pre, keyPre) => { const seen = {}; for (const k of S.children(pid)) { const n = S.get(k); if (!n) continue; const nm = String(n.name || n.type), c = seen[nm] = (seen[nm] || 0) + 1;
      const path = pre ? pre + '/' + k : k, key = keyPre + '\u0001' + nm + (c > 1 ? '\u0002' + c : ''); const info = {path: path, key: key, type: n.type, comp: n.comp};
      byPath.set(path, info); if (!byKey.has(key)) byKey.set(key, info); if (CONT[n.type] === 1 && n.type !== 'INSTANCE') walk(k, path, key); } };
    if (S.has(compId)) walk(compId, '', '');
    return {byPath: byPath, byKey: byKey};
  }
  function carryOverrides(ov, fromComp, toComp, prefix) {
    const a = nameIndex(fromComp), b = nameIndex(toComp), out = {}, pre = prefix ? prefix + '/' : '';
    for (const k in ov) {
      if (prefix && k !== prefix && k.indexOf(pre) !== 0) { out[k] = ov[k]; continue; }          /* not below the swapped layer */
      if (k === prefix || k === '') { out[k] = ov[k]; continue; }
      const rel = k.slice(pre.length), segs = rel.split('/'); let n = segs.length, info = null;
      while (n > 0 && !(info = a.byPath.get(segs.slice(0, n).join('/')))) n--;
      if (!info) continue;
      const to = b.byKey.get(info.key); if (!to || to.type !== info.type) continue;
      const rest = segs.slice(n); if (rest.length && !(to.type === 'INSTANCE' && to.comp === info.comp)) continue;
      out[pre + to.path + (rest.length ? '/' + rest.join('/') : '')] = ov[k];
    }
    return out;
  }
  /* swap(instId, compId)            the instance itself
     swap(instId, compId, path)      a nested instance inside it (an override of its `comp`) */
  function swap(instId, compId, path) {
    const inst = S.get(instId), c = S.get(compId);
    if (!inst || inst.type !== 'INSTANCE' || !c || c.type !== 'COMPONENT' || !guard()) return false;
    if (S.isAncestor(compId, instId)) { UI.toast('A component can not hold an instance of itself.'); return false; }
    return S.tx('Swap instance', () => {
      if (!path) {
        const old = inst.comp; if (old === compId) return false;
        const oc = S.get(old), p = {comp: compId, ov: carryOverrides(ovOf(inst), old, compId, '')};
        if (!Object.keys(p.ov).length) p.ov = null;
        if (!oc || (Math.abs(W(inst) - W(oc)) < EPS && Math.abs(H(inst) - H(oc)) < EPS)) { p.w = W(c); p.h = H(c); }    /* it had the component's size: take the new one */
        if (inst.name === compName(old)) p.name = compName(compId);
        return S.set(instId, p);
      }
      const v = vfind(buildTree(instId, inst), path); if (!v || !v.isRoot || v.comp === compId) return false;
      const ov = carryOverrides(ovOf(inst), v.comp, compId, path), e = Object.assign({}, ov[path] || {}, {comp: compId});
      const base = baseValue(instId, path, 'comp'); if (base === compId) delete e.comp;
      if (Object.keys(e).length) ov[path] = e; else delete ov[path];
      return S.set(instId, {ov: Object.keys(ov).length ? ov : null});
    }) || false;
  }

  /* ---- alt-drag / duplicate / paste of a main component make an instance; deleting one detaches its instances first */
  const act = T.act, origDup = act.duplicate, origPaste = act.paste, origClip = act.clip, origRemove = S.remove;
  act.duplicate = function (quiet) {
    let ids, mains;
    try { ids = tops(); mains = ids.filter(standalone); } catch (e) { mains = []; }
    if (!mains.length || !canEdit()) return origDup.call(act, quiet);
    const out = [];
    S.tx('Duplicate', () => {
      const rest = ids.filter(id => mains.indexOf(id) < 0);
      if (rest.length) { HD.sel.set(rest); for (const id of (origDup.call(act, true) || [])) out.push(id); }
      for (const id of mains) { const n = S.get(id), d = quiet ? 0 : 24, i = createInstance(id, n.parent, num(n.x, 0) + d, num(n.y, 0) + d, nextSibling(id)); if (i) out.push(i); }
    });
    HD.sel.set(out);
    return out;
  };
  act.paste = function (at) {
    let data = null, fileId = HD.app && HD.app.file && HD.app.file.id;
    try { data = origClip.call(act); } catch (e) { data = null; }
    const isM = t => t && t.p && t.p.type === 'COMPONENT' && standalone(t.id);
    if (!data || !Array.isArray(data.nodes) || data.file !== fileId || !data.nodes.some(isM)) return origPaste.call(act, at);
    const nodes = data.nodes.map(t => { if (!isM(t)) return t; const c = S.get(t.id), p = {type: 'INSTANCE', name: compName(t.id), comp: t.id, x: num(c.x, 0), y: num(c.y, 0), w: W(c), h: H(c)}; if (c.rot) p.rot = 0; if (c.visible === false) p.visible = true;
      return {id: t.id, p: p, kids: [], cw: t.cw}; });
    const swapped = Object.assign({}, data, {nodes: nodes});
    act.clip = function () { return swapped; };
    try { return origPaste.call(act, at); } finally { act.clip = origClip; }
  };
  S.remove = function (ids) {
    let list = [], doomed = null;
    try {
      const arr = Array.isArray(ids) ? ids : ids instanceof Set ? Array.from(ids) : ids === undefined || ids === null ? [] : [ids];
      const gone = new Set(), comps = new Set();
      for (const id of arr) S.walk(id, (k, n) => { gone.add(k); if (n.type === 'COMPONENT') comps.add(k); });
      if (comps.size && !S.readOnly) { doomed = comps; S.walk(ROOT, (id, n) => { if (n.type !== 'INSTANCE') return undefined; if (!gone.has(id)) list.push(id); return false; }); }
    } catch (e) { list = []; doomed = null; }
    if (!doomed) return origRemove.call(S, ids);
    return S.tx('Delete', () => {
      for (const id of list) {
        const n = S.get(id); if (!n) continue;
        if (doomed.has(n.comp)) { detachOne(id); continue; }
        const ov = ovOf(n); let next = null;                                    /* a swap override that points at a deleted component goes back to the original */
        for (const k in ov) if (ov[k] && doomed.has(ov[k].comp)) { if (!next) next = Object.assign({}, ov); const e = Object.assign({}, ov[k]); delete e.comp; if (Object.keys(e).length) next[k] = e; else delete next[k]; }
        if (next) S.set(id, {ov: Object.keys(next).length ? next : null});
      }
      return origRemove.call(S, ids);
    }) || false;
  };

  /* ---------------------------------------------------------------- variants */
  function parseVariant(name) {
    const out = {}; let any = false;
    for (const part of String(name || '').split(',')) { const i = part.indexOf('='); if (i <= 0) continue; const k = part.slice(0, i).trim(), v = part.slice(i + 1).trim(); if (k) { out[k] = v; any = true; } }
    return any ? out : null;
  }
  function variantName(vals, order) { return order.filter(k => vals[k] !== undefined).map(k => k + '=' + vals[k]).join(', '); }
  /* {props: [names in first-seen order], values: {prop: [values]}, variants: [{id, vals}]} */
  function setInfo(setId) {
    const info = {id: setId, props: [], values: {}, variants: []};
    for (const id of S.children(setId)) { if (!isMain(id)) continue; const vals = parseVariant((S.get(id) || {}).name) || {'Property 1': String((S.get(id) || {}).name || 'Default')};
      info.variants.push({id: id, vals: vals});
      for (const k in vals) { if (!info.values[k]) { info.values[k] = []; info.props.push(k); } if (info.values[k].indexOf(vals[k]) < 0) info.values[k].push(vals[k]); } }
    return info;
  }
  const BOOL_ON = {true: 1, on: 1, yes: 1}, BOOL_OFF = {false: 1, off: 1, no: 1};
  function boolPair(values) {
    if (!values.length || values.length > 2) return null;
    const low = values.map(v => String(v).toLowerCase()); let on = null, off = null;
    for (let i = 0; i < low.length; i++) { if (BOOL_ON[low[i]]) on = values[i]; else if (BOOL_OFF[low[i]]) off = values[i]; else return null; }
    return on !== null || off !== null ? {on: on, off: off} : null;
  }
  /* the variant that has prop = value and agrees with `have` on as many other properties as it can */
  function pickVariant(info, have, prop, value) {
    let best = null, score = -1;
    for (const v of info.variants) { if (v.vals[prop] !== value) continue; let s = 0; for (const k of info.props) if (k !== prop && v.vals[k] === have[k]) s++; if (s > score) { score = s; best = v; } }
    return best;
  }
  /* variantInfo(compId) -> {set, info, vals} when the component is a variant, else null */
  function variantInfo(compId) {
    if (!compId || !inSet(compId)) return null;
    const info = setInfo(S.parent(compId)), me = info.variants.find(v => v.id === compId);
    return me ? {set: info.id, info: info, vals: me.vals} : null;
  }
  function setVariant(instId, prop, value, path) {
    const v = path ? vnode(instId, path) : null, compId = path ? (v && v.comp) : (S.get(instId) || {}).comp, vi = variantInfo(compId);
    if (!vi) return false;
    const to = pickVariant(vi.info, vi.vals, prop, value); if (!to) { UI.toast('There is no variant with ' + prop + ' = ' + value + '.'); return false; }
    return swap(instId, to.id, path);
  }
  function combineAsVariants(ids) {
    if (!guard()) return null;
    ids = S.order([].concat(ids || tops()).filter(standalone));
    if (!ids.length) { UI.toast('Select one or more components to combine.'); return null; }
    if (ids.some(id => hasAncestorOfType(id, {COMPONENT: 1, INSTANCE: 1}))) { UI.toast('These components can not be combined here.'); return null; }
    const names = ids.map(id => String((S.get(id) || {}).name || 'Component')), cut = names[0].lastIndexOf('/');
    const pre = cut > 0 && names.every(n => n.slice(0, cut + 1) === names[0].slice(0, cut + 1)) ? names[0].slice(0, cut) : '';
    let setId = null;
    S.tx('Combine as variants', () => {
      const last = ids[ids.length - 1], parent = S.parent(last), before = nextSibling(last), b = boxInParent(ids, parent), pad = 20;
      setId = S.create('COMPONENT_SET', parent, {name: pre || names[0], x: r2(b.x - pad), y: r2(b.y - pad), w: r2(b.w + pad * 2), h: r2(b.h + pad * 2), fills: [],
        strokes: [{type: 'solid', color: VIOLET, opacity: 1, visible: true}], strokeWeight: 1, dash: [6, 4], radius: 8, clip: false}, before || undefined);
      S.move(ids, setId, null);
      ids.forEach((id, i) => { const nm = names[i]; if (!parseVariant(nm)) S.set(id, {name: 'Property 1=' + (pre ? nm.slice(cut + 1) : ids.length === 1 ? 'Default' : nm)}); });
    });
    if (setId) HD.sel.set([setId]);
    return setId;
  }
  function renameVariantProp(setId, from, to) {
    to = String(to || '').replace(/[=,]/g, ' ').trim(); if (!to || to === from || !guard()) return;
    const info = setInfo(setId); if (info.props.indexOf(to) >= 0) { UI.toast('There is already a property called ' + to + '.'); return; }
    S.tx('Rename property', () => { for (const v of info.variants) { if (v.vals[from] === undefined) continue; const vals = {}; for (const k of info.props) if (v.vals[k] !== undefined) vals[k === from ? to : k] = v.vals[k];
      S.set(v.id, {name: variantName(vals, info.props.map(k => k === from ? to : k))}); } });
  }
  function renameVariantValue(setId, prop, from, to) {
    to = String(to || '').replace(/[=,]/g, ' ').trim(); if (!to || to === from || !guard()) return;
    const info = setInfo(setId);
    S.tx('Rename value', () => { for (const v of info.variants) if (v.vals[prop] === from) S.set(v.id, {name: variantName(Object.assign({}, v.vals, {[prop]: to}), info.props)}); });
  }
  function setVariantValue(compId, prop, to) {
    to = String(to || '').replace(/[=,]/g, ' ').trim(); const vi = variantInfo(compId); if (!to || !vi || !guard()) return;
    S.tx('Change variant', () => S.set(compId, {name: variantName(Object.assign({}, vi.vals, {[prop]: to}), vi.info.props.indexOf(prop) >= 0 ? vi.info.props : vi.info.props.concat([prop]))}));
  }
  function addVariantProp(setId, name, value) {
    if (!guard()) return; const info = setInfo(setId); let n = info.props.length + 1; name = String(name || '').replace(/[=,]/g, ' ').trim();
    if (!name) { while (info.props.indexOf('Property ' + n) >= 0) n++; name = 'Property ' + n; }
    if (info.props.indexOf(name) >= 0) { UI.toast('There is already a property called ' + name + '.'); return; }
    S.tx('Add property', () => { for (const v of info.variants) S.set(v.id, {name: variantName(Object.assign({}, v.vals, {[name]: value || 'Default'}), info.props.concat([name]))}); });
  }
  function removeVariantProp(setId, name) {
    if (!guard()) return; const info = setInfo(setId); if (info.props.length < 2) { UI.toast('A set of variants needs at least one property.'); return; }
    S.tx('Remove property', () => { for (const v of info.variants) { const vals = Object.assign({}, v.vals); delete vals[name]; S.set(v.id, {name: variantName(vals, info.props)}); } });
  }
  /* a copy of a real subtree with fresh ids; returns the new id, fills map (old id -> new id) */
  function copyTree(srcId, parentId, before, map, patch) {
    const n = S.get(srcId); if (!n) return null;
    const p = cleanProps(n); if (patch) Object.assign(p, patch);
    const id = S.create(n.type, parentId, p, before || undefined);
    map[srcId] = id;
    for (const k of S.children(srcId)) copyTree(k, id, null, map);
    return id;
  }
  function remapPath(path, map) { return String(path).split('/').map(s => map[s] || s).join('/'); }
  function fixCopied(map) {
    for (const old in map) { const id = map[old], n = S.get(id); if (!n) continue; const p = {};
      if (Array.isArray(n.cprops)) p.cprops = n.cprops.map(c => Object.assign({}, c, {target: remapPath(c.target, map)}));
      if (Array.isArray(n.reactions) && n.reactions.some(r => r && map[r.to])) p.reactions = n.reactions.map(r => r && map[r.to] ? Object.assign({}, r, {to: map[r.to]}) : r);
      if (Object.keys(p).length) S.set(id, p); }
  }
  function addVariant(setId) {
    if (!guard()) return null; const info = setInfo(setId); if (!info.variants.length) return null;
    const src = info.variants[info.variants.length - 1], sn = S.get(src.id), set = S.get(setId), prop = info.props[info.props.length - 1] || 'Property 1';
    let n = info.variants.length + 1; while ((info.values[prop] || []).indexOf('Variant ' + n) >= 0) n++;
    let id = null;
    S.tx('Add variant', () => {
      const map = {}, y = num(sn.y, 0) + H(sn) + 20;
      id = copyTree(src.id, setId, null, map, {name: variantName(Object.assign({}, src.vals, {[prop]: 'Variant ' + n}), info.props.length ? info.props : [prop]), y: y});
      fixCopied(map);
      if (y + H(sn) + 20 > H(set)) S.set(setId, {h: r2(y + H(sn) + 20)});
    });
    if (id) HD.sel.set([id]);
    return id;
  }

  /* ---------------------------------------------------------------- component properties (cprops) */
  function cpropsOf(compId) { const n = S.get(compId); return n && Array.isArray(n.cprops) ? n.cprops.filter(c => c && typeof c.target === 'string' && (c.type === 'text' || c.type === 'bool' || c.type === 'swap')) : []; }
  function pathInComp(compId, nodeId) { const segs = []; let c = nodeId, g = 0; while (c && c !== compId && g++ < 500) { segs.unshift(c); c = S.parent(c); } return c === compId ? segs.join('/') : null; }
  function nodeAtPath(compId, path) { const segs = String(path).split('/'), id = segs[segs.length - 1]; return S.has(id) && pathInComp(compId, id) === path ? id : null; }
  function addCprop(compId, type, nodeId, name) {
    if (!guard()) return null; const path = pathInComp(compId, nodeId), n = S.get(nodeId); if (!path || !n) return null;
    if (type === 'text' && n.type !== 'TEXT') { UI.toast('A text property needs a text layer.'); return null; }
    if (type === 'swap' && n.type !== 'INSTANCE') { UI.toast('A swap property needs an instance inside the component.'); return null; }
    const cp = {id: newKey('p'), name: String(name || (type === 'bool' ? 'Show ' : '') + (n.name || 'Layer')).slice(0, 80), type: type, target: path,
      def: type === 'text' ? String(val(n, 'chars') || '') : type === 'bool' ? n.visible !== false : (n.comp || '')};
    S.tx('Add property', () => S.set(compId, {cprops: cpropsOf(compId).concat([cp])}));
    return cp.id;
  }
  function updateCprop(compId, pid, patch) { if (!guard()) return; S.tx('Change property', () => S.set(compId, {cprops: cpropsOf(compId).map(c => c.id === pid ? Object.assign({}, c, patch) : c)})); }
  function removeCprop(compId, pid) { if (!guard()) return; S.tx('Remove property', () => { const l = cpropsOf(compId).filter(c => c.id !== pid); S.set(compId, {cprops: l.length ? l : null}); }); }
  /* the value an instance shows for a property (path = where the instance sits inside another one, "" = itself) */
  function cpropValue(instId, path, cp) {
    const v = vnode(instId, path ? path + '/' + cp.target : cp.target); if (!v) return cp.def;
    return cp.type === 'text' ? String(val(v.n, 'chars') || '') : cp.type === 'bool' ? v.n.visible !== false : v.comp;
  }
  function setCprop(instId, path, cp, value) {
    const target = path ? path + '/' + cp.target : cp.target;
    if (cp.type === 'swap') return swap(instId, value, target);
    return setOverride(instId, target, cp.type === 'text' ? {chars: String(value)} : {visible: !!value}, 'Change ' + cp.name);
  }

  /* ---------------------------------------------------------------- styles */
  const LINK = {fill: 'fillStyle', text: 'textStyle', effect: 'effectStyle'}, KIND_LABEL = {fill: 'Colour', text: 'Text', effect: 'Effect'};
  function styles() { const s = rootNode().styles; return s && typeof s === 'object' ? s : {}; }
  function styleList(kind) { const s = styles(), out = []; for (const sid in s) if (s[sid] && (!kind || s[sid].kind === kind)) out.push(Object.assign({id: sid}, s[sid])); return out.sort((a, b) => String(a.name).toLowerCase() < String(b.name).toLowerCase() ? -1 : 1); }
  function styleValueOf(kind, id) {
    if (kind === 'fill') return clone(S.prop(id, 'fills') || []);
    if (kind === 'effect') return clone(S.prop(id, 'effects') || []);
    const o = {}; for (const k of TEXT_KEYS) { const v = S.prop(id, k); if (v !== undefined) o[k] = v; } return o;
  }
  function stylePatch(kind, value) { return kind === 'fill' ? {fills: clone(value) || []} : kind === 'effect' ? {effects: clone(value) || []} : Object.assign({}, value); }
  function matchesStyle(kind, node, value) {
    if (kind === 'fill') return same(val(node, 'fills') || [], value || []);
    if (kind === 'effect') return same(val(node, 'effects') || [], value || []);
    for (const k of TEXT_KEYS) if (value && value[k] !== undefined && !same(val(node, k), value[k])) return false;
    return true;
  }
  function createStyle(kind, name, value, linkIds) {
    if (!guard() || !LINK[kind]) return null;
    const sid = newKey('s'), all = styles(); let nm = String(name || '').trim(), n = 1;
    if (!nm) { const used = new Set(styleList(kind).map(s => s.name)); do { nm = KIND_LABEL[kind] + ' ' + n++; } while (used.has(nm)); }
    S.tx('Create style', () => {
      S.set(ROOT, {styles: Object.assign({}, all, {[sid]: {kind: kind, name: nm.slice(0, 80), value: clone(value)}})});
      for (const id of (linkIds || [])) if (S.has(id)) S.set(id, Object.assign(stylePatch(kind, value), {[LINK[kind]]: sid}));
    });
    return sid;
  }
  function applyStyle(sid, ids) {
    const s = styles()[sid]; if (!s || !guard()) return false;
    S.tx('Apply style', () => { for (const id of [].concat(ids)) { if (!S.has(id)) continue; if (s.kind === 'text' && typeOf(id) !== 'TEXT') continue; S.set(id, Object.assign(stylePatch(s.kind, s.value), {[LINK[s.kind]]: sid})); } });
    return true;
  }
  function detachStyle(kind, ids) { if (!guard()) return; S.tx('Detach style', () => { for (const id of [].concat(ids)) if (S.has(id)) S.set(id, {[LINK[kind]]: typeOf(id) === 'INSTANCE' && kind !== 'text' && S.prop(id, LINK[kind]) ? '' : null}); }); }
  /* rename and / or give a style a new value: the root AND every layer linked to it change in ONE tx */
  function updateStyle(sid, patch, g) {
    const all = styles(), s = all[sid]; if (!s) return false;
    return write('Edit style', () => {
      const next = Object.assign({}, s); if (patch.name !== undefined) next.name = String(patch.name).slice(0, 80) || s.name; if (patch.value !== undefined) next.value = clone(patch.value);
      S.set(ROOT, {styles: Object.assign({}, all, {[sid]: next})});
      if (patch.value === undefined) return true;
      const link = LINK[s.kind], p = stylePatch(s.kind, next.value);
      S.walk(ROOT, (id, n) => {
        if (n[link] === sid) S.set(id, p);
        if (n.type === 'INSTANCE' && n.ov) { let ov = null; for (const k in n.ov) if (n.ov[k] && n.ov[k][link] === sid) { if (!ov) ov = Object.assign({}, n.ov); ov[k] = Object.assign({}, n.ov[k], p); } if (ov) S.set(id, {ov: ov}); }
      });
      return true;
    }, g);
  }
  function deleteStyle(sid) {
    const all = styles(), s = all[sid]; if (!s || !guard()) return;
    S.tx('Delete style', () => { const next = Object.assign({}, all); delete next[sid]; S.set(ROOT, {styles: Object.keys(next).length ? next : null});
      S.walk(ROOT, (id, n) => { if (n[LINK[s.kind]] === sid) S.set(id, {[LINK[s.kind]]: null}); }); });
  }
  function styleUsers(sid) { const s = styles()[sid], out = []; if (!s) return out; S.walk(ROOT, (id, n) => { if (n[LINK[s.kind]] === sid) out.push(id); }); return out; }

  /* ---------------------------------------------------------------- variables + modes */
  const BINDS = [
    {key: 'fill', label: 'Fill colour', type: 'color', ok: n => n.type !== 'GROUP' && n.type !== 'LINE'},
    {key: 'w', label: 'Width', type: 'number', ok: n => n.type !== 'GROUP'}, {key: 'h', label: 'Height', type: 'number', ok: n => n.type !== 'GROUP' && n.type !== 'LINE'},
    {key: 'gap', label: 'Gap', type: 'number', ok: n => isAuto(n)}, {key: 'padding', label: 'Padding', type: 'number', ok: n => isAuto(n)},
    {key: 'radius', label: 'Corner radius', type: 'number', ok: n => ({RECT: 1, FRAME: 1, COMPONENT: 1, INSTANCE: 1, SECTION: 1, POLYGON: 1, STAR: 1})[n.type] === 1},
    {key: 'opacity', label: 'Opacity', type: 'number', ok: () => true}, {key: 'chars', label: 'Text', type: 'string', ok: n => n.type === 'TEXT'}, {key: 'visible', label: 'Visible', type: 'bool', ok: () => true}
  ];
  const BIND_BY = {}; for (const b of BINDS) BIND_BY[b.key] = b;
  const BIND_PROP = {fill: 'fills', w: 'w', h: 'h', gap: 'layout', padding: 'layout', radius: 'radius', opacity: 'opacity', chars: 'chars', visible: 'visible'};
  const VAR_TYPES = [['color', 'Colour'], ['number', 'Number'], ['string', 'Text'], ['bool', 'True / false']];
  const VAR_DEF = {color: '#6E55F0', number: 0, string: '', bool: true};
  function isAuto(n) { return !!(n.layout && n.layout.mode && n.layout.mode !== 'none'); }
  function vars() { const v = rootNode().vars; return v && typeof v === 'object' ? v : {}; }
  function modes() { const m = rootNode().modes; return Array.isArray(m) && m.length ? m : ['Mode 1']; }
  function varList(type) { const v = vars(), out = []; for (const id in v) if (v[id] && (!type || v[id].type === type)) out.push(Object.assign({id: id}, v[id])); return out.sort((a, b) => String(a.name).toLowerCase() < String(b.name).toLowerCase() ? -1 : 1); }
  function bindsOf(n) { const out = {}, b = n && n.bind; if (b && typeof b === 'object') for (const k in b) if (k.charAt(0) === '$' && BIND_BY[k.slice(1)] && typeof b[k] === 'string') out[k.slice(1)] = b[k]; return out; }
  /* the mode a node resolves in: the nearest `mode` on itself or above, else the first mode */
  function modeOf(id) {
    const list = modes(); let c = id, g = 0;
    while (c && g++ < 2000) { const n = S.get(c); if (!n) break; if (typeof n.mode === 'string' && list.indexOf(n.mode) >= 0) return n.mode; c = n.parent; }
    return list[0];
  }
  function varValue(vid, mode) {
    const v = vars()[vid]; if (!v || !v.modes) return undefined;
    if (mode !== undefined && v.modes[mode] !== undefined) return v.modes[mode];
    const first = modes()[0]; if (v.modes[first] !== undefined) return v.modes[first];
    for (const k in v.modes) return v.modes[k];
    return VAR_DEF[v.type];
  }
  /* what a bound property has to be set to (null = it already is) */
  function bindPatch(id, key, value) {
    const n = S.get(id); if (!n || value === undefined) return null;
    if (key === 'fill') { if (typeof value !== 'string') return null; const f = S.prop(id, 'fills'), a = Array.isArray(f) ? f.slice() : [];
      if (a.length && a[0] && a[0].type === 'solid') { if (a[0].color === value) return null; a[0] = Object.assign({}, a[0], {color: value}); } else a[0] = {type: 'solid', color: value, opacity: 1, visible: true};
      return {fills: a}; }
    if (key === 'w' || key === 'h') { const v = Math.max(0.01, +value); return isFinite(v) && Math.abs(num(n[key], 100) - v) > 1e-6 ? {[key]: v} : null; }
    if (key === 'gap' || key === 'padding') { const v = +value; if (!isFinite(v) || !n.layout) return null; const l = Object.assign({}, n.layout);
      if (key === 'gap') { if (l.gap === v) return null; l.gap = v; } else { if (same(l.pad, [v, v, v, v])) return null; l.pad = [v, v, v, v]; } return {layout: l}; }
    if (key === 'radius') { const v = Math.max(0, +value); return isFinite(v) && !same(val(n, 'radius'), v) ? {radius: v} : null; }
    if (key === 'opacity') { let v = +value; if (!isFinite(v)) return null; if (v > 1) v = v / 100; v = Math.max(0, Math.min(1, v)); return Math.abs(num(val(n, 'opacity'), 1) - v) > 1e-6 ? {opacity: v} : null; }
    if (key === 'chars') { const v = String(value); return val(n, 'chars') === v ? null : {chars: v}; }
    if (key === 'visible') { const v = !!value; return (n.visible !== false) === v ? null : {visible: v}; }
    return null;
  }
  function resolveNode(id) {
    const n = S.get(id); if (!n || !n.bind) return false;
    const b = bindsOf(n), mode = modeOf(id); let any = false;
    for (const key in b) { const p = bindPatch(id, key, varValue(b[key], mode)); if (p) { S.set(id, p); any = true; } }
    return any;
  }
  function resolveSubtree(id) { S.walk(id, (k, n) => { if (n.bind) resolveNode(k); }); }
  function resolveAll() { return write('Apply variables', () => { resolveSubtree(ROOT); return true; }); }
  function writeVars(next, nextModes) { const p = {vars: Object.keys(next).length ? next : null}; if (nextModes !== undefined) p.modes = nextModes; S.set(ROOT, p); }
  function addVar(type, name) {
    if (!guard() || VAR_DEF[type] === undefined) return null;
    const all = vars(), list = modes(), vid = newKey('v'), used = new Set(varList().map(v => v.name)); let nm = String(name || '').trim(), n = 1;
    if (!nm) { const base = {color: 'colour', number: 'number', string: 'text', bool: 'switch'}[type]; do { nm = base + ' ' + n++; } while (used.has(nm)); }
    const m = {}; for (const k of list) m[k] = VAR_DEF[type];
    S.tx('Add variable', () => writeVars(Object.assign({}, all, {[vid]: {name: nm.slice(0, 120), type: type, modes: m}}), rootNode().modes && rootNode().modes.length ? undefined : list));
    return vid;
  }
  function renameVar(vid, name) { const all = vars(), v = all[vid]; name = String(name || '').trim().slice(0, 120); if (!v || !name || name === v.name || !guard()) return; S.tx('Rename variable', () => writeVars(Object.assign({}, all, {[vid]: Object.assign({}, v, {name: name})}))); }
  /* a new value for one mode: the variable AND every layer bound to it change in one tx */
  function setVarValue(vid, mode, value, g) {
    const all = vars(), v = all[vid]; if (!v) return false;
    if (v.type === 'number') { value = +value; if (!isFinite(value)) return false; } else if (v.type === 'bool') value = !!value; else value = String(value);
    return write('Change variable', () => { writeVars(Object.assign({}, all, {[vid]: Object.assign({}, v, {modes: Object.assign({}, v.modes, {[mode]: value})})}));
      S.walk(ROOT, (id, n) => { if (!n.bind) return; const b = bindsOf(n); for (const k in b) if (b[k] === vid) { resolveNode(id); break; } }); return true; }, g);
  }
  function deleteVar(vid) {
    const all = vars(); if (!all[vid] || !guard()) return;
    S.tx('Delete variable', () => { const next = Object.assign({}, all); delete next[vid]; writeVars(next);
      S.walk(ROOT, (id, n) => { if (!n.bind) return; let b = null; for (const k in n.bind) if (n.bind[k] === vid) { if (!b) b = Object.assign({}, n.bind); delete b[k]; } if (b) S.set(id, {bind: Object.keys(b).length ? b : null}); }); });
  }
  function addMode(name) {
    if (!guard()) return null; const list = modes(), all = vars(); let nm = String(name || '').trim(), n = list.length + 1;
    if (!nm) { do { nm = 'Mode ' + n++; } while (list.indexOf(nm) >= 0); } if (list.indexOf(nm) >= 0) { UI.toast('There is already a mode called ' + nm + '.'); return null; }
    S.tx('Add mode', () => { const next = {}; for (const id in all) next[id] = Object.assign({}, all[id], {modes: Object.assign({}, all[id].modes, {[nm]: varValue(id, list[0])})}); writeVars(next, list.concat([nm])); });
    return nm;
  }
  function renameMode(from, to) {
    const list = modes(), all = vars(); to = String(to || '').trim().slice(0, 60); if (!to || to === from || list.indexOf(from) < 0 || !guard()) return;
    if (list.indexOf(to) >= 0) { UI.toast('There is already a mode called ' + to + '.'); return; }
    S.tx('Rename mode', () => { const next = {}; for (const id in all) { const m = {}; for (const k in all[id].modes) m[k === from ? to : k] = all[id].modes[k]; if (m[to] === undefined) m[to] = varValue(id, from); next[id] = Object.assign({}, all[id], {modes: m}); }
      writeVars(next, list.map(m => m === from ? to : m)); S.walk(ROOT, (id, n) => { if (n.mode === from) S.set(id, {mode: to}); }); });
  }
  function deleteMode(name) {
    const list = modes(), all = vars(); if (list.length < 2 || list.indexOf(name) < 0 || !guard()) return;
    S.tx('Delete mode', () => { const next = {}; for (const id in all) { const m = Object.assign({}, all[id].modes); delete m[name]; next[id] = Object.assign({}, all[id], {modes: m}); }
      writeVars(next, list.filter(m => m !== name)); S.walk(ROOT, (id, n) => { if (n.mode === name) S.set(id, {mode: null}); }); resolveSubtree(ROOT); });
  }
  /* bind(ids, key, vid | null): the link in node.bind AND the resolved value, one tx */
  function bind(ids, key, vid) {
    if (!guard() || !BIND_BY[key]) return false; const v = vid ? vars()[vid] : null;
    if (vid && (!v || v.type !== BIND_BY[key].type)) { UI.toast('That variable does not fit this property.'); return false; }
    return S.tx(vid ? 'Bind variable' : 'Unbind variable', () => { for (const id of [].concat(ids)) { const n = S.get(id); if (!n) continue;
      const b = Object.assign({}, n.bind && typeof n.bind === 'object' ? n.bind : {}); delete b[key]; if (vid) b['$' + key] = vid; else delete b['$' + key];
      S.set(id, {bind: Object.keys(b).length ? b : null}); if (vid) { const p = bindPatch(id, key, varValue(vid, modeOf(id))); if (p) S.set(id, p); } } return true; }) || false;
  }
  /* a frame's mode (null = the one above it); every bound layer below gets its values again in the same tx */
  function setMode(ids, mode) {
    if (!guard()) return false; if (mode && modes().indexOf(mode) < 0) return false;
    return S.tx('Change mode', () => { for (const id of [].concat(ids)) if (S.has(id)) { S.set(id, {mode: mode || null}); resolveSubtree(id); } return true; }) || false;
  }

  /* ---- inside every local tx (after the layout engine): a linked / bound value that was changed by hand lets go of
     its link, and a layer that moved under another mode gets its bound values again. Never runs for remote ops. */
  function txHook(props) {
    const extra = new Set();
    if (!props || typeof props.forEach !== 'function') return extra;
    const all = styles(), list = [];
    props.forEach((ps, id) => { if (ps && ps.size) list.push([id, Array.from(ps)]); });
    for (const item of list) {
      const id = item[0], ps = new Set(item[1]), n = S.get(id); if (!n || id === ROOT) continue;
      for (const kind in LINK) {
        const link = LINK[kind], sid = kind === 'text' ? n[link] : S.prop(id, link); if (!sid || ps.has(link)) continue;
        const touched = kind === 'fill' ? ps.has('fills') : kind === 'effect' ? ps.has('effects') : TEXT_KEYS.some(k => ps.has(k)); if (!touched) continue;
        const s = all[sid], probe = kind === 'text' ? n : {type: n.type, fills: S.prop(id, 'fills'), effects: S.prop(id, 'effects')};
        if (!s || !matchesStyle(kind, probe, s.value)) { S.set(id, {[link]: n[link] === undefined && n.type === 'INSTANCE' ? '' : null}); extra.add(id); }
      }
      if (n.bind && !ps.has('bind')) {
        const b = bindsOf(n), mode = modeOf(id); let nb = null;
        for (const key in b) { if (!ps.has(BIND_PROP[key])) continue; if (bindPatch(id, key, varValue(b[key], mode)) === null) continue; if (!nb) nb = Object.assign({}, n.bind); delete nb['$' + key]; }
        if (nb) { S.set(id, {bind: Object.keys(nb).length ? nb : null}); extra.add(id); }
      }
      if ((ps.has('mode') || ps.has('parent')) && rootNode().vars) S.walk(id, (k, kn) => { if (kn.bind && resolveNode(k)) extra.add(k); });
    }
    return extra;
  }
  if (HD.layout && typeof HD.layout.run === 'function' && !HD.layout.run.hdComp) {
    const origRun = HD.layout.run;
    const run = function (changedIds, changedProps) {
      const out = origRun.call(HD.layout, changedIds, changedProps);
      let extra = null;
      try { extra = txHook(changedProps); } catch (e) { if (window.console) console.error('[HD.comp]', e); }
      if (extra && extra.size) { try { origRun.call(HD.layout, extra, changedProps); } catch (e) { if (window.console) console.error('[HD.comp]', e); } }
      return out;
    };
    run.hdComp = true;
    HD.layout.run = run;
  }

  /* ================================================================ the interface */
  const TYPE_ICON = {FRAME: 'frame', GROUP: 'group', SECTION: 'section', RECT: 'rect', ELLIPSE: 'ellipse', LINE: 'line', POLYGON: 'polygon', STAR: 'star', VECTOR: 'vector', TEXT: 'text', COMPONENT: 'component', COMPONENT_SET: 'component', INSTANCE: 'instance'};
  const TYPE_LABEL = {RECT: 'Rectangle', ELLIPSE: 'Ellipse', LINE: 'Line', POLYGON: 'Polygon', STAR: 'Star', VECTOR: 'Vector', TEXT: 'Text', FRAME: 'Frame', GROUP: 'Group', SECTION: 'Section', COMPONENT: 'Component', COMPONENT_SET: 'Component set', INSTANCE: 'Instance'};
  function ibtn(name, title, run, cls) { const b = h('button', {class: 'hd-ib' + (cls ? ' ' + cls : ''), type: 'button', title: title, 'aria-label': title}, icon(name)); if (run) b.addEventListener('click', run); return b; }
  function tbtn(text, title, run, cls) { const b = h('button', {class: 'hd-btn hdc-mini' + (cls ? ' ' + cls : ''), type: 'button', title: title || text, text: text}); if (run) b.addEventListener('click', run); return b; }
  function lab(text) { return h('span', {class: 'hdc-lab', title: text, text: text}); }
  function onSync(fn) { UI.state.syncs.push(fn); fn(); return fn; }
  function typing(t) { return !!(t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)); }
  /* a text box that commits on Enter / when it loses focus (never on every key: the panel may be rebuilt by the change) */
  function textIn(o) {
    const el = h(o.area ? 'textarea' : 'input', {class: 'hd-in' + (o.area ? ' hdc-area' : '') + (o.cls ? ' ' + o.cls : ''), 'aria-label': o.label, title: o.label, spellcheck: 'false', placeholder: o.placeholder || null, maxlength: String(o.max || 400)});
    if (!o.area) el.type = 'text';
    const show = () => { if (document.activeElement === el) return; const v = o.get(); el.value = v === undefined || v === null ? '' : String(v); el.disabled = !canEdit(); };
    const commit = () => { const v = el.value; if (v !== String(o.get() === undefined || o.get() === null ? '' : o.get())) o.set(v); };
    el.addEventListener('change', commit);
    el.addEventListener('keydown', ev => { if (ev.key === 'Enter' && (!o.area || ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); el.blur(); } else if (ev.key === 'Escape') { ev.preventDefault(); ev.stopPropagation(); el.value = String(o.get() === undefined || o.get() === null ? '' : o.get()); el.blur(); } });
    if (o.sync === false) show(); else onSync(show);
    el._show = show;
    return el;
  }
  function switchCtl(get, set, label, sync) {
    const b = h('button', {class: 'hdc-switch', type: 'button', role: 'switch', 'aria-label': label, title: label}, h('i'));
    const show = () => { const v = get() === true; b.classList.toggle('on', v); b.setAttribute('aria-checked', String(v)); b.disabled = !canEdit(); };
    b.addEventListener('click', () => { set(!(get() === true)); show(); });
    if (sync === false) show(); else onSync(show);
    return b;
  }
  function thumb(id, bw, bh) {
    const n = S.get(id); let cv;
    const w = n ? Math.max(1, W(n)) : 1, hh = n ? Math.max(1, H(n)) : 1, dpr = Math.min(2, window.devicePixelRatio || 1), s = Math.min(bw / w, bh / hh, 2);
    try { cv = HD.render.toCanvas(id, s * dpr); } catch (e) { cv = document.createElement('canvas'); cv.width = cv.height = 1; }
    const k = Math.min(1, bw / (cv.width / dpr), bh / (cv.height / dpr));
    cv.style.width = Math.max(1, Math.round(cv.width / dpr * k)) + 'px'; cv.style.height = Math.max(1, Math.round(cv.height / dpr * k)) + 'px';
    cv.className = 'hdc-thumb'; cv.setAttribute('aria-hidden', 'true');
    return cv;
  }

  /* ---------------------------------------------------------------- deep select inside an instance */
  const sub = {inst: null, path: ''};
  let settingSel = false, wiredCanvas = null;
  function subV() { return sub.inst ? vnode(sub.inst, sub.path) : null; }
  function touchUI() { UI.refresh(); if (HD.render && HD.render.invalidate) HD.render.invalidate(); }
  function setSub(instId, path) {
    if (!path || typeOf(instId) !== 'INSTANCE' || !vnode(instId, path)) { clearSub(); return false; }
    sub.inst = instId; sub.path = path;
    if (!(HD.sel.ids.length === 1 && HD.sel.ids[0] === instId)) { settingSel = true; try { const pg = S.pageOf(instId); if (pg && pg !== HD.sel.page) UI.setPage(pg); HD.sel.set([instId]); } finally { settingSel = false; } }
    if (UI.state.rightTab !== 'design') UI.state.rightTab = 'design';
    touchUI();
    return true;
  }
  function clearSub() { if (!sub.inst) return; sub.inst = null; sub.path = ''; touchUI(); }
  function worldOf(ev) { const r = T.canvas.getBoundingClientRect(); return HD.render.screenToWorld(ev.clientX - r.left, ev.clientY - r.top); }
  function stop(ev) { ev.stopImmediatePropagation(); ev.preventDefault(); }
  function lockedChain(id) { return U().chain(id).some(c => S.prop(c, 'locked') === true); }
  function focusSubText() { const el = UI.state.designBody && UI.state.designBody.querySelector('.hdc-sub textarea'); if (el) { el.focus(); el.select(); return true; } return false; }
  function onDbl(ev) {
    if (T.current !== 'move' || !UI.mounted) return;
    const w = worldOf(ev); let instId = sub.inst;
    if (!instId) { const ids = HD.sel.ids; if (ids.length !== 1 || typeOf(ids[0]) !== 'INSTANCE') return; instId = ids[0]; }
    if (HD.render.hitTest(w[0], w[1], {deep: true}) !== instId) return;
    const chain = hitChain(instId, w[0], w[1]); if (!chain.length) return;
    let next = chain[0];
    if (sub.inst) { const i = chain.findIndex(v => v.path === sub.path); if (i >= 0) { next = chain[i + 1] || null; if (!next) { stop(ev); setTimeout(focusSubText, 0); return; } } }
    stop(ev);
    if (next) setSub(instId, next.path);
  }
  function onDown(ev) {
    if (ev.button !== 0 || T.current !== 'move' || !UI.mounted || T.state.spaceDown || T.panOnly) return;
    const w = worldOf(ev);
    if (sub.inst) {
      const chain = HD.render.hitTest(w[0], w[1], {deep: true}) === sub.inst ? hitChain(sub.inst, w[0], w[1]) : [];
      if (!chain.length) { clearSub(); return; }                               /* a click somewhere else: the ordinary tool takes over */
      const depth = sub.path.split('/').length, pick = (ev.ctrlKey || ev.metaKey) ? chain[chain.length - 1] : chain[Math.min(depth, chain.length) - 1];
      stop(ev); T.canvas.focus({preventScroll: true});
      setSub(sub.inst, pick.path);
      return;
    }
    if ((ev.ctrlKey || ev.metaKey) && !ev.shiftKey) {
      const deep = HD.render.hitTest(w[0], w[1], {deep: true});
      if (!deep || typeOf(deep) !== 'INSTANCE' || lockedChain(deep)) return;
      const chain = hitChain(deep, w[0], w[1]); if (!chain.length) return;
      stop(ev); T.canvas.focus({preventScroll: true});
      setSub(deep, chain[chain.length - 1].path);
    }
  }
  function wireCanvas() { const cv = T.canvas; if (!cv || cv === wiredCanvas) return; wiredCanvas = cv; cv.addEventListener('dblclick', onDbl, true); cv.addEventListener('pointerdown', onDown, true); }
  window.addEventListener('keydown', ev => {
    if (!sub.inst || !UI.mounted || typing(ev.target) || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (document.querySelector('.hd-modal') || document.querySelector('.hd-pop')) return;
    const v = subV(); if (!v) return;
    if (ev.key === 'Escape') { stop(ev); const i = sub.path.lastIndexOf('/'); if (i > 0) setSub(sub.inst, sub.path.slice(0, i)); else clearSub(); }
    else if (ev.key === 'Delete' || ev.key === 'Backspace') { stop(ev); if (guard()) setOverride(sub.inst, sub.path, {visible: false}, 'Hide in instance'); }
    else if (ev.key === 'Enter') { stop(ev); if (v.n.type === 'TEXT') focusSubText(); else if (v.kids.length) setSub(sub.inst, v.kids[v.kids.length - 1].path); }
    else if (ev.key === 'Tab') { const sib = v.parent ? v.parent.kids : []; if (sib.length > 1) { stop(ev); const i = sib.indexOf(v); setSub(sub.inst, sib[(i + (ev.shiftKey ? 1 : sib.length - 1)) % sib.length].path); } }
  }, true);
  HD.sel.on('change', () => { if (sub.inst && !settingSel && !(HD.sel.ids.length === 1 && HD.sel.ids[0] === sub.inst)) { sub.inst = null; sub.path = ''; } ensurePanel(); });
  HD.render.addOverlay(ctx => {
    wireCanvas(); ensurePanel();
    const v = subV(); if (!v) return;
    const pts = vcorners(v).map(p => HD.render.worldToScreen(p[0], p[1]));
    ctx.save(); ctx.lineJoin = 'round'; ctx.strokeStyle = VIOLET; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < 4; i++) ctx.lineTo(pts[i][0], pts[i][1]); ctx.closePath(); ctx.stroke();
    ctx.fillStyle = '#FFFFFF'; ctx.lineWidth = 1.5;
    for (const p of pts) { ctx.beginPath(); ctx.rect(Math.round(p[0]) - 2.5, Math.round(p[1]) - 2.5, 5, 5); ctx.fill(); ctx.stroke(); }
    ctx.restore();
  });

  /* ---------------------------------------------------------------- the Design panel: our sections are put into the first-wave panel */
  let observed = null, mo = null, structVer = 1, deferred = false;
  const inj = {sig: '', syncs: null};
  function ensurePanel() {
    const el = UI.state.designBody; if (!el || !UI.mounted) return;
    if (el !== observed) { if (mo) mo.disconnect(); observed = el; inj.sig = ''; mo = new MutationObserver(() => { try { inject(); } catch (e) { if (window.console) console.error('[HD.comp]', e); } }); mo.observe(el, {childList: true}); }
    inject();
  }
  function inject() {
    const el = UI.state.designBody; if (!el || !UI.mounted || UI.state.rightTab !== 'design' || !el.firstChild) return;
    if (el.querySelector(':scope > .hdc-mark') && inj.syncs === UI.state.syncs) return;
    build(el);
  }
  function busy(el) {
    if (document.body.classList.contains('hd-scrub')) return 'scrub';
    const a = document.activeElement; if (a && typing(a) && el.contains(a) && a.closest('.hdc-inj')) return 'focus';
    return '';
  }
  function panelSync() {
    const el = UI.state.designBody; if (!el || !UI.mounted) return;
    if (sub.inst && !subV()) { sub.inst = null; sub.path = ''; }
    const sig = sigNow(); if (sig === inj.sig) return;
    const why = busy(el);
    if (why) { if (!deferred) { deferred = true; const again = () => { deferred = false; setTimeout(() => UI.refresh(), 0); };
      if (why === 'scrub') window.addEventListener('pointerup', again, {once: true, capture: true}); else el.addEventListener('focusout', again, {once: true}); } return; }
    build(el);
  }
  function ovSig(n) { const o = ovOf(n), out = []; for (const k in o) out.push(k + ':' + Object.keys(o[k] || {}).join(',') + (o[k] && o[k].comp ? '=' + o[k].comp : '')); return out.join(';'); }
  function paintSig(a) { return Array.isArray(a) ? a.length + ':' + a.map(p => (p && p.type) || '').join(',') : '0'; }
  function sigNow() {
    const ids = selIds(), parts = [ids.length > 6 ? ids.length + ':' + ids[0] : ids.join(','), sub.inst || '', sub.path, rootVer, structVer, canEdit() ? 1 : 0];
    for (const id of ids.slice(0, 6)) { const n = S.get(id); if (!n) continue;
      parts.push(n.type, n.comp || '', ovSig(n), Object.keys(ROOT_OV).filter(k => n[k] !== undefined).join(','), JSON.stringify(n.bind || 0), n.mode || '', n.fillStyle || '', n.textStyle || '', n.effectStyle || '', n.libHash || '', isAuto(n) ? 1 : 0); }
    const v = subV();
    if (v) parts.push(v.n.type, v.comp, paintSig(v.n.fills), paintSig(v.n.strokes), v.n.fillStyle || '', v.n.textStyle || '', v.n.effectStyle || '', Array.isArray(v.n.radius) ? 'r4' : 'r1');
    return parts.join('|');
  }
  function sec(el, title, actions, ref, cls) { const s = UI.section(el, title, actions, {cls: 'hdc-inj' + (cls ? ' ' + cls : '')}); if (ref) el.insertBefore(s.el, ref); return s; }
  function build(el) {
    for (const x of Array.from(el.querySelectorAll('.hdc-inj'))) x.remove();
    const v = subV(), ids = selIds();
    el.classList.toggle('hdc-subsel', !!v);
    el.appendChild(h('span', {class: 'hdc-mark hdc-inj', hidden: true}));
    inj.syncs = UI.state.syncs;
    if (inj.syncs.indexOf(panelSync) < 0) inj.syncs.push(panelSync);
    if (v) buildSub(el, v);
    else if (!ids.length) buildEmpty(el);
    else buildSelection(el, ids);
    inj.sig = sigNow();
  }

  /* ---- a selection of real layers */
  function buildSelection(el, ids) {
    const anchor = el.querySelector(':scope > .hd-alignrow'), ref = anchor ? anchor.nextSibling : el.firstChild, edit = canEdit();
    const one = ids.length === 1 ? ids[0] : null, t = one ? typeOf(one) : '';
    if (ids.every(id => typeOf(id) === 'INSTANCE')) secInstance(el, ids, ref);
    else if (t === 'COMPONENT') secComponent(el, one, ref);
    else if (t === 'COMPONENT_SET') secSet(el, one, ref);
    if (edit && ids.length && ids.every(standalone) && !hasAncestorOfType(ids[0], {COMPONENT: 1})) {
      const s = sec(el, 'Variants', null, ref, 'hdc-tight');
      s.body.appendChild(UI.row(tbtn('Combine as variants', 'Put ' + (ids.length === 1 ? 'this component' : 'these components') + ' into one set of variants', () => combineAsVariants(ids), 'grow')));
    }
    secVariables(el, ids, el.querySelector(':scope > section[aria-label="Export"]'));
    styleButtons(el, {ids: ids});
  }
  function instMenu(anchor, ids) {
    const one = ids.length === 1 ? ids[0] : null;
    UI.menu(anchor, [one && {label: 'Go to main component', icon: 'component', disabled: !mainOf(one), run: () => goToMain(one)}, one && {label: 'Swap instance\u2026', icon: 'rotate', disabled: !canEdit(), run: () => swapPicker(anchor, one, '')}, '-',
      {label: 'Reset all changes', icon: 'undo', disabled: !canEdit() || !ids.some(id => listOverrides(id).length), run: () => resetAll(ids)},
      {label: 'Detach instance', icon: 'link', keys: 'mod+alt+b', disabled: !canEdit(), run: () => detach(ids)}], {label: 'Instance'});
  }
  /* the main component + swap, the variant controls and the component properties of one (possibly nested) instance */
  function instControls(body, instId, path) {
    const compId = () => path ? ((vnode(instId, path) || {}).comp || '') : ((S.get(instId) || {}).comp || '');
    const cid = compId(), missing = !S.has(cid), edit = canEdit();
    const mainT = h('span', {class: 'hdc-main-t'}), mainB = h('button', {class: 'hdc-main', type: 'button', title: 'Go to the main component'}, icon('component', 14), mainT);
    mainB.addEventListener('click', () => { const c = compId(); if (!S.has(c)) return; clearSub(); const pg = S.pageOf(c); if (pg && pg !== HD.sel.page) UI.setPage(pg); HD.sel.set([c]); T.view.fit([c]); UI.revealLayers([c]); });
    onSync(() => { const c = compId(); mainT.textContent = S.has(c) ? compName(c) : 'Missing component'; mainB.disabled = !S.has(c); });
    const sw = tbtn('Swap', 'Swap for another component', () => swapPicker(sw, instId, path)); sw.disabled = !edit;
    body.appendChild(UI.row(mainB, sw));
    if (missing) { body.appendChild(h('p', {class: 'hd-note', text: 'The main component of this instance is not in this file. Swap it for another component, or detach it to keep it as a plain frame.'})); return; }
    const vi = variantInfo(cid);
    if (vi) for (const prop of vi.info.props) {
      const values = vi.info.values[prop], bp = boolPair(values), cur = () => { const x = variantInfo(compId()); return x ? x.vals[prop] : undefined; };
      const ctl = bp && bp.on !== null && bp.off !== null ? switchCtl(() => cur() === bp.on, on => setVariant(instId, prop, on ? bp.on : bp.off, path), prop)
        : h('label', {class: 'hd-sfield'}, UI.select(values.map(x => [x, x]), () => cur(), x => setVariant(instId, prop, x, path), prop));
      body.appendChild(h('div', {class: 'hd-row hdc-prow', 'data-prop': prop}, lab(prop), ctl));
    }
    for (const cp of cpropsOf(cid)) {
      let ctl;
      if (cp.type === 'text') ctl = textIn({label: cp.name, get: () => cpropValue(instId, path, cp), set: x => setCprop(instId, path, cp, x), max: 20000});
      else if (cp.type === 'bool') ctl = switchCtl(() => cpropValue(instId, path, cp) === true, x => setCprop(instId, path, cp, x), cp.name);
      else { const opts = []; for (const c of listComponents()) for (const vId of c.variants) opts.push([vId, c.kind === 'set' ? c.name + ' / ' + ((S.get(vId) || {}).name || '') : c.name]);
        ctl = h('label', {class: 'hd-sfield'}, UI.select(opts, () => cpropValue(instId, path, cp), x => setCprop(instId, path, cp, x), cp.name)); }
      body.appendChild(h('div', {class: 'hd-row hdc-prow', 'data-cprop': cp.id}, lab(cp.name), ctl));
    }
  }
  function changeChips(body, instId, path) {
    const all = listOverrides(instId).filter(o => path === undefined || o.path === path || (path && o.path.indexOf(path + '/') === 0)); if (!all.length) return false;
    const box = h('div', {class: 'hdc-chips', role: 'list', 'aria-label': 'Changes in this instance'});
    for (const o of all.slice(0, 14)) { const b = h('button', {class: 'hdc-chip', type: 'button', role: 'listitem', title: 'Reset: back to the main component', 'data-path': o.path, 'data-prop': o.prop}, h('span', {text: o.label + (o.layer && path === undefined ? ' \u00B7 ' + o.layer : '')}), icon('close', 10));
      b.disabled = !canEdit(); b.addEventListener('click', () => resetOverride(instId, o.path, o.prop)); box.appendChild(b); }
    if (all.length > 14) box.appendChild(h('span', {class: 'hd-dimtext', text: 'and ' + (all.length - 14) + ' more'}));
    body.appendChild(h('div', {class: 'hdc-sublab', text: 'Changed here'})); body.appendChild(box);
    return true;
  }
  function secInstance(el, ids, ref) {
    const one = ids.length === 1 ? ids[0] : null;
    const s = sec(el, ids.length === 1 ? 'Instance' : ids.length + ' instances', [{el: ibtn('dots', 'Instance options', ev => instMenu(ev.currentTarget, ids))}], ref, 'hdc-inst');
    if (!one) { const r = UI.row(tbtn('Reset all changes', '', () => resetAll(ids), 'grow'), tbtn('Detach', 'Detach: turn into plain frames', () => detach(ids))); for (const b of r.children) b.disabled = !canEdit(); s.body.appendChild(r); return; }
    instControls(s.body, one, '');
    if (changeChips(s.body, one, undefined)) { const b = h('button', {class: 'hd-linkbtn hdc-resetall', type: 'button', text: 'Reset all changes', on: {click: () => resetAll([one])}}); b.disabled = !canEdit(); s.body.appendChild(b); }
    const tree = vtree(one); if (!tree || !tree.kids.length) return;
    const rows = []; vwalk(tree, (v, d) => { if (v !== tree && rows.length < 81) rows.push([v, d]); });
    s.body.appendChild(h('div', {class: 'hdc-sublab', text: 'Layers in this instance'}));
    const list = h('div', {class: 'hdc-vtree', role: 'tree', 'aria-label': 'Layers in this instance'});
    for (const r of rows.slice(0, 80)) { const v = r[0], changed = isOverridden(one, v.path);
      const b = h('button', {class: 'hdc-vrow' + (v.n.visible === false ? ' off' : ''), type: 'button', role: 'treeitem', title: 'Select this layer inside the instance', 'data-path': v.path, style: {paddingLeft: (6 + (r[1] - 1) * 12) + 'px'}},
        h('span', {class: 'hd-ltype'}, icon(TYPE_ICON[v.n.type] || 'rect', 14)), h('span', {class: 'hd-lname', text: v.n.type === 'TEXT' && !v.n.name ? String(v.n.chars || 'Text') : (v.n.name || TYPE_LABEL[v.n.type] || 'Layer')}), changed ? h('i', {class: 'hdc-dot', title: 'Changed in this instance'}) : null);
      b.addEventListener('click', () => setSub(one, v.path)); list.appendChild(b); }
    if (rows.length > 80) list.appendChild(h('span', {class: 'hd-dimtext', text: 'Only the first 80 layers are listed.'}));
    s.body.appendChild(list);
  }
  function secComponent(el, id, ref) {
    const edit = canEdit(), s = sec(el, 'Component', [edit ? {el: ibtn('plus', 'Add a property', ev => cpropMenu(ev.currentTarget, id))} : null], ref, 'hdc-comp');
    s.body.appendChild(UI.row(textIn({label: 'Description', placeholder: 'Describe when to use it', get: () => S.prop(id, 'desc') || '', set: v => write('Description', () => S.set(id, {desc: v.slice(0, 2000) || null})), max: 2000})));
    const users = instancesOf(id).length;
    s.body.appendChild(UI.row(h('span', {class: 'hd-dimtext hd-grow1', text: users === 1 ? '1 instance in this file' : users + ' instances in this file'}), users ? tbtn('Select', 'Select the instances on this page', () => { const list = instancesOf(id).filter(i => S.pageOf(i) === HD.sel.page); if (list.length) HD.sel.set(list); else UI.toast('The instances are on other pages.'); }) : null));
    const vi = variantInfo(id);
    if (vi) { s.body.appendChild(h('div', {class: 'hdc-sublab', text: 'This variant'}));
      for (const prop of vi.info.props) s.body.appendChild(h('div', {class: 'hd-row hdc-prow'}, lab(prop), textIn({label: prop, get: () => { const x = variantInfo(id); return x ? x.vals[prop] || '' : ''; }, set: v => setVariantValue(id, prop, v), max: 80}))); }
    const cps = cpropsOf(id);
    if (cps.length) { s.body.appendChild(h('div', {class: 'hdc-sublab', text: 'Properties'}));
      for (const cp of cps) { const rm = ibtn('minus', 'Remove this property', () => removeCprop(id, cp.id), 'sm'); rm.disabled = !edit;
        s.body.appendChild(h('div', {class: 'hd-row hdc-cprow', 'data-cprop': cp.id}, h('span', {class: 'hdc-kind', title: cp.type === 'text' ? 'Text property' : cp.type === 'bool' ? 'Show / hide property' : 'Swap property'}, icon(cp.type === 'text' ? 'text' : cp.type === 'bool' ? 'eye' : 'instance', 14)),
          textIn({label: 'Property name', get: () => (cpropsOf(id).find(c => c.id === cp.id) || cp).name, set: v => { if (v.trim()) updateCprop(id, cp.id, {name: v.trim().slice(0, 80)}); }, max: 80}), rm)); } }
    const n = S.get(id);
    if (n && n.libSrc && n.libSrc.file) { s.body.appendChild(h('div', {class: 'hdc-sublab', text: 'Library'}));
      const b = tbtn('Update', 'Fetch this component again from the file it came from', () => updateFromLibrary([id])); b.disabled = !edit;
      s.body.appendChild(UI.row(h('span', {class: 'hd-dimtext hd-grow1 hdc-clip', text: 'Copied from ' + (n.libSrc.name || 'another file')}), b)); }
  }
  function cpropMenu(anchor, compId) {
    const items = []; let count = 0;
    S.walk(compId, (id, n) => { if (id === compId || count > 40) return undefined; count++; const nm = n.name || TYPE_LABEL[n.type] || 'Layer';
      if (n.type === 'TEXT') items.push({label: 'Text of \u201C' + nm + '\u201D', icon: 'text', run: () => addCprop(compId, 'text', id)});
      if (n.type === 'INSTANCE') items.push({label: 'Swap \u201C' + nm + '\u201D', icon: 'instance', run: () => addCprop(compId, 'swap', id)});
      items.push({label: 'Show / hide \u201C' + nm + '\u201D', icon: 'eye', run: () => addCprop(compId, 'bool', id)});
      return n.type === 'INSTANCE' ? false : undefined; });
    if (!items.length) { UI.toast('Add a layer inside the component first.'); return; }
    UI.menu(anchor, [{head: 'Let instances change\u2026'}].concat(items), {label: 'Add a property'});
  }
  function secSet(el, id, ref) {
    const edit = canEdit(), s = sec(el, 'Variants', [edit ? {el: ibtn('plus', 'Add a property', () => addVariantProp(id))} : null], ref, 'hdc-set'), info = setInfo(id);
    for (const prop of info.props) {
      const rm = ibtn('minus', 'Remove this property', () => removeVariantProp(id, prop), 'sm'); rm.disabled = !edit || info.props.length < 2;
      s.body.appendChild(h('div', {class: 'hd-row hdc-cprow', 'data-prop': prop}, textIn({label: 'Property name', cls: 'hdc-strong', get: () => prop, set: v => renameVariantProp(id, prop, v), max: 60}), rm));
      const vals = h('div', {class: 'hdc-vals'});
      for (const value of info.values[prop]) vals.appendChild(textIn({label: 'Value of ' + prop, get: () => value, set: v => renameVariantValue(id, prop, value, v), max: 60}));
      s.body.appendChild(vals);
    }
    const add = tbtn('Add variant', 'A copy of the last variant, ready to change', () => addVariant(id), 'grow'); add.disabled = !edit;
    s.body.appendChild(UI.row(h('span', {class: 'hd-dimtext hd-grow1', text: info.variants.length === 1 ? '1 variant' : info.variants.length + ' variants'}), add));
  }
  function swapPicker(anchor, instId, path) {
    const q = h('input', {class: 'hd-in hd-search', type: 'search', placeholder: 'Search components', 'aria-label': 'Search components', autofocus: true}), list = h('div', {class: 'hdc-picklist', role: 'listbox', 'aria-label': 'Components'});
    const cur = path ? ((vnode(instId, path) || {}).comp || '') : ((S.get(instId) || {}).comp || ''); let handle = null;
    const draw = () => { clear(list); const s = q.value.trim().toLowerCase(); let n = 0;
      for (const c of listComponents()) for (const vId of c.variants) { const name = c.kind === 'set' ? c.name + ' / ' + ((S.get(vId) || {}).name || '') : c.name; if (s && name.toLowerCase().indexOf(s) < 0) continue; if (++n > 60) break;
        list.appendChild(h('button', {class: 'hd-mi hdc-pick' + (vId === cur ? ' cur' : ''), type: 'button', role: 'option', 'aria-selected': String(vId === cur), 'data-id': vId, on: {click: () => { if (handle) handle.close(); swap(instId, vId, path); }}},
          h('span', {class: 'hdc-pickth'}, thumb(vId, 28, 28)), h('span', {class: 'hd-mlab', text: name}), vId === cur ? icon('check') : null)); }
      if (!list.firstChild) list.appendChild(h('div', {class: 'hd-none pad', text: 'No component with that name.'})); };
    q.addEventListener('input', draw); q.addEventListener('keydown', ev => { if (ev.key === 'Enter') { const b = list.querySelector('.hd-mi:not(.cur)') || list.querySelector('.hd-mi'); if (b) b.click(); } });
    draw(); handle = UI.pop(anchor, h('div', {class: 'hd-fontpick'}, q, list), {cls: 'hd-pop-font hdc-pop', label: 'Swap instance', side: 'left'});
  }

  /* ---- the layer that is selected INSIDE an instance: every control writes an override */
  const ROUNDS = {RECT: 1, FRAME: 1, COMPONENT: 1, INSTANCE: 1, SECTION: 1, POLYGON: 1, STAR: 1};
  const WEIGHTS = [[100, 'Thin'], [200, 'Extra light'], [300, 'Light'], [400, 'Regular'], [500, 'Medium'], [600, 'Semi bold'], [700, 'Bold'], [800, 'Extra bold'], [900, 'Black']];
  function paintLines(body, title, list, setList, level) {
    const n = list().length;
    for (let i = n - 1; i >= 0; i--) body.appendChild(UI.colorLine({title: title, level: level || 0, get: () => list()[i], set: (p, g) => { const a = list().slice(); if (i < a.length) { a[i] = p; setList(a, g); } }, remove: () => { const a = list().slice(); a.splice(i, 1); setList(a); }}));
  }
  function buildSub(el, v) {
    const instId = sub.inst, path = sub.path, edit = canEdit(), type = v.n.type, inst = S.get(instId) || {};
    const get = name => { const x = subV(); return x ? val(x.n, name) : undefined; };
    const set = (patch, label, g) => setOverride(instId, path, patch, label, g);
    const wrap = h('div', {class: 'hdc-sub hdc-inj', 'data-path': path}); el.appendChild(wrap);
    wrap.appendChild(h('div', {class: 'hd-selhead hdc-subhead'}, ibtn('back', 'Back to the instance  (Esc)', () => clearSub(), 'sm'), h('span', {class: 'hd-ltype'}, icon(TYPE_ICON[type] || 'rect', 14)),
      h('span', {class: 'hd-selname', text: v.n.name || TYPE_LABEL[type] || 'Layer'}), h('span', {class: 'hd-seltype hdc-clip', text: 'in ' + (inst.name || 'instance')})));
    const mark = (s, props) => {
      if (!props.some(p => isOverridden(instId, path, p))) return;
      s.head.querySelector('.hd-stitle').appendChild(h('i', {class: 'hdc-dot', title: 'Changed in this instance'}));
      const b = ibtn('undo', 'Reset to the main component', () => { const p = {}; for (const k of props) p[k] = undefined; set(p, 'Reset override'); }, 'hdc-reset'); b.disabled = !edit; s.acts.insertBefore(b, s.acts.firstChild);
    };
    const nf = (name, title, label, o) => UI.numField(Object.assign({label: label, title: title, get: () => num(get(name), 0), set: (x, g) => set({[name]: x}, title, g)}, o || {}));
    if (v.isRoot) { const s = UI.section(wrap, 'Nested instance', null, {cls: 'hdc-inst'}); instControls(s.body, instId, path); mark(s, ['comp']); }
    const sl = UI.section(wrap, 'Layer');
    sl.body.appendChild(UI.row(lab('Visible'), switchCtl(() => get('visible') !== false, on => set({visible: on}, on ? 'Show in instance' : 'Hide in instance'), 'Visible in this instance'),
      UI.numField({icon: 'opacity', title: 'Opacity', unit: '%', min: 0, max: 100, get: () => Math.round(num(get('opacity'), 1) * 100), set: (x, g) => set({opacity: Math.round(x) / 100}, 'Opacity', g)})));
    sl.body.appendChild(UI.row(nf('x', 'X position', 'X'), nf('y', 'Y position', 'Y')));
    if (type !== 'LINE') sl.body.appendChild(UI.row(nf('w', 'Width', 'W', {min: 0.01}), nf('h', 'Height', 'H', {min: 0.01})));
    if (ROUNDS[type] && !Array.isArray(get('radius'))) sl.body.appendChild(UI.row(nf('radius', 'Corner radius', null, {icon: 'radius', min: 0}), h('span', {class: 'hd-field ghost'})));
    mark(sl, ['visible', 'opacity', 'x', 'y', 'w', 'h', 'radius']);
    if (changeChips(sl.body, instId, path)) { /* the chips reset one change each */ }
    if (type === 'TEXT') {
      const st = UI.section(wrap, 'Text');
      st.body.appendChild(UI.row(textIn({area: true, label: 'Text in this instance', get: () => String(get('chars') || ''), set: x => set({chars: x}, 'Change text'), max: 20000})));
      st.body.appendChild(UI.row(h('label', {class: 'hd-sfield grow'}, UI.select(WEIGHTS, () => num(get('fontWeight'), 400), x => set({fontWeight: x}, 'Font weight'), 'Font weight')),
        UI.numField({label: 'Size', title: 'Font size', min: 1, max: 2000, get: () => num(get('fontSize'), 16), set: (x, g) => set({fontSize: x}, 'Font size', g)})));
      mark(st, ['chars', 'fontSize', 'fontWeight', 'textStyle']);
    }
    if (type !== 'GROUP') {
      for (const pair of [['fills', 'Fill', '#D9D9D9'], ['strokes', 'Stroke', '#1A1A1F']]) {
        const name = pair[0], title = pair[1], list = () => { const a = get(name); return Array.isArray(a) ? a : []; }, setList = (arr, g) => set({[name]: arr}, title, g);
        const s = UI.section(wrap, title, [edit ? {icon: 'plus', title: 'Add a ' + title.toLowerCase(), run: () => setList(list().concat([{type: 'solid', color: pair[2], opacity: 1, visible: true}]))} : null], {cls: list().length ? '' : 'bare'});
        paintLines(s.body, title, list, setList, 0);
        if (name === 'strokes' && list().length) s.body.appendChild(UI.row(UI.numField({label: 'Weight', wide: true, title: 'Stroke weight', min: 0, max: 1000, get: () => num(get('strokeWeight'), 1), set: (x, g) => set({strokeWeight: x}, 'Stroke weight', g)})));
        mark(s, name === 'fills' ? ['fills', 'fillStyle'] : ['strokes', 'strokeWeight']);
      }
    }
    wrap.appendChild(h('p', {class: 'hd-note pad', text: 'This layer belongs to the main component. What you change here stays in this instance only.'}));
    styleButtons(wrap, {inst: instId, path: path});
  }

  /* ---- nothing selected: the file's styles and variables */
  function swatchOf(paints) {
    const el = h('span', {class: 'hd-sw hdc-sw', 'aria-hidden': 'true'}), p = Array.isArray(paints) ? paints.filter(x => x && x.visible !== false).pop() : null;
    const col = (c, a) => { const m = /^#([0-9a-f]{6})/i.exec(String(c || '')); if (!m) return 'transparent'; const x = parseInt(m[1], 16); return 'rgba(' + (x >> 16) + ',' + ((x >> 8) & 255) + ',' + (x & 255) + ',' + (a === undefined ? 1 : a) + ')'; };
    if (p && p.type === 'solid') el.style.background = col(p.color, p.opacity);
    else if (p && Array.isArray(p.stops) && p.stops.length) el.style.background = 'linear-gradient(135deg,' + p.stops.map(s => col(s.color, s.opacity)).join(',') + ')';
    else if (p) el.style.background = 'repeating-linear-gradient(45deg,#C9C9CF 0 4px,#E9E9EE 4px 8px)';
    return el;
  }
  function stylePreview(s) {
    if (s.kind === 'fill') return swatchOf(s.value);
    if (s.kind === 'text') return h('span', {class: 'hdc-ag', 'aria-hidden': 'true', text: 'Ag'});
    return h('span', {class: 'hdc-ag', 'aria-hidden': 'true'}, icon('copy', 14));
  }
  const STYLE_NEW = {fill: () => [{type: 'solid', color: '#6E55F0', opacity: 1, visible: true}], text: () => ({font: 'Inter', fontSize: 16, fontWeight: 400, lineHeight: 'auto', letterSpacing: 0}),
    effect: () => [{type: 'drop', x: 0, y: 4, blur: 12, spread: 0, color: '#000000', opacity: 0.25, visible: true}]};
  function buildEmpty(el) {
    const ref = el.querySelector(':scope > section[aria-label="Getting started"]'), edit = canEdit();
    const s = sec(el, 'Styles', [edit ? {el: ibtn('plus', 'New style', ev => { const a = ev.currentTarget; UI.menu(a, ['fill', 'text', 'effect'].map(k => ({label: KIND_LABEL[k] + ' style', run: () => { const sid = createStyle(k, '', STYLE_NEW[k]()); if (sid) setTimeout(() => { const row = el.querySelector('.hdc-srow[data-sid="' + sid + '"]'); styleEditor(row || a, sid, 0); }, 60); }})), {label: 'New style'}); })} : null], ref, 'hdc-styles');
    const all = styleList();
    if (!all.length) s.body.appendChild(h('p', {class: 'hd-note', text: 'Colour, text and effect styles of this file show up here. Make one with +, or from a layer\u2019s Fill, Text or Effects section.'}));
    for (const kind of ['fill', 'text', 'effect']) { const list = all.filter(x => x.kind === kind); if (!list.length) continue;
      s.body.appendChild(h('div', {class: 'hdc-sublab', text: KIND_LABEL[kind]}));
      for (const st of list) { const b = h('button', {class: 'hdc-srow', type: 'button', title: 'Edit this style', 'data-sid': st.id}, stylePreview(st), h('span', {class: 'hd-lname', text: st.name}));
        b.addEventListener('click', () => styleEditor(b, st.id, 0)); s.body.appendChild(b); } }
    const vs = varList().length, ms = modes().length, sv = sec(el, 'Variables', null, ref, 'hdc-varsec');
    sv.body.appendChild(UI.row(h('span', {class: 'hd-dimtext hd-grow1', text: vs ? (vs === 1 ? '1 variable' : vs + ' variables') + ', ' + (ms === 1 ? '1 mode' : ms + ' modes') : 'Colours, numbers and texts you can reuse'}), tbtn(vs ? 'Open' : 'Create', 'Open the variables of this file', openVariables)));
  }

  /* ---- variables of a selection: what is bound, and the mode of a frame */
  function secVariables(el, ids, ref) {
    const edit = canEdit(), nodes = ids.map(id => S.get(id)).filter(Boolean), all = varList(); if (!nodes.length) return;
    const keys = BINDS.filter(b => nodes.every(n => b.ok(n))), bound = keys.filter(b => nodes.some(n => bindsOf(n)[b.key]));
    const showMode = (rootNode().modes || []).length > 1 && nodes.every(n => CONT[n.type] === 1);
    if (!all.length && !bound.length) return;
    const s = sec(el, 'Variables', [edit ? {el: ibtn('plus', 'Bind a property to a variable', ev => bindMenu(ev.currentTarget, ids, keys))} : null], ref, 'hdc-varsec' + (bound.length || showMode ? '' : ' bare'));
    for (const b of bound) { const opts = [['', 'None']].concat(varList(b.type).map(v => [v.id, v.name]));
      s.body.appendChild(h('div', {class: 'hd-row hdc-prow', 'data-bind': b.key}, lab(b.label), h('label', {class: 'hd-sfield'}, UI.select(opts, () => { let first, has = false; for (const id of ids) { const v = bindsOf(S.get(id))[b.key] || ''; if (!has) { first = v; has = true; } else if (v !== first) return UI.MIXED; } return first; }, v => bind(ids, b.key, v || null), b.label + ' variable')))); }
    if (showMode) s.body.appendChild(h('div', {class: 'hd-row hdc-prow', 'data-bind': 'mode'}, lab('Mode'), h('label', {class: 'hd-sfield'}, UI.select([['', 'Same as above']].concat(modes().map(m => [m, m])), () => { let first, has = false; for (const id of ids) { const v = (S.get(id) || {}).mode || ''; if (!has) { first = v; has = true; } else if (v !== first) return UI.MIXED; } return first; }, v => setMode(ids, v || null), 'Mode for the layers inside'))));
  }
  function varHint(v) { const x = varValue(v.id, modes()[0]); return v.type === 'bool' ? (x ? 'true' : 'false') : String(x === undefined ? '' : x).slice(0, 14); }
  function bindMenu(anchor, ids, keys) {
    const items = keys.map(b => { const list = varList(b.type); return {label: b.label, disabled: !list.length, sub: list.map(v => ({label: v.name, hint: varHint(v), run: () => bind(ids, b.key, v.id)}))}; });
    UI.menu(anchor, [{head: 'Bind to a variable'}].concat(items).concat(['-', {label: 'Open variables\u2026', icon: 'sliders', run: openVariables}]), {label: 'Bind a property'});
  }

  /* ---- the small style button in the Fill / Text / Effects sections (first-wave sections and our own) */
  function linkOfTarget(kind, target) {
    const link = LINK[kind];
    if (target.inst) { const v = vnode(target.inst, target.path); return v ? (v.n[link] || '') : ''; }
    let first, has = false;
    for (const id of target.ids) { const x = (kind === 'text' ? (S.get(id) || {})[link] : S.prop(id, link)) || ''; if (!has) { first = x; has = true; } else if (x !== first) return ''; }
    return first || '';
  }
  function styleButtons(container, target) {
    for (const kind of ['fill', 'text', 'effect']) {
      const title = kind === 'fill' ? 'Fill' : kind === 'text' ? 'Text' : 'Effects', s = container.querySelector(':scope > section[aria-label="' + title + '"]');
      if (!s || s.querySelector('.hdc-stylebtn')) continue;
      if (kind === 'text' && target.ids && !target.ids.every(id => typeOf(id) === 'TEXT')) continue;
      const acts = s.querySelector('.hd-sacts'), body = s.querySelector('.hd-sbody'); if (!acts || !body) continue;
      const btn = ibtn('tidy', KIND_LABEL[kind] + ' styles', () => stylePop(btn, kind, target), 'hdc-stylebtn hdc-inj'); acts.insertBefore(btn, acts.firstChild);
      const chip = h('div', {class: 'hdc-stylechip hdc-inj', hidden: true}); body.insertBefore(chip, body.firstChild);
      onSync(() => {
        const sid = linkOfTarget(kind, target), st = sid ? styles()[sid] : null, key = st ? sid + '\u0001' + st.name + '\u0001' + JSON.stringify(st.value).length : '';
        btn.classList.toggle('on', !!st); s.classList.toggle('hdc-linked', !!st); chip.hidden = !st;
        if (chip.dataset.k === key) return; chip.dataset.k = key; clear(chip); if (!st) return;
        const nameB = h('button', {class: 'hdc-stylename', type: 'button', title: 'Edit this style'}, stylePreview(st), h('span', {class: 'hd-lname', text: st.name}));
        nameB.addEventListener('click', () => styleEditor(chip, sid, 0));
        const off = ibtn('link', 'Detach from the style', () => unlinkTarget(kind, target), 'sm'); off.disabled = !canEdit();
        chip.appendChild(nameB); chip.appendChild(off);
      });
    }
  }
  function unlinkTarget(kind, target) { if (target.inst) setOverride(target.inst, target.path, {[LINK[kind]]: ''}, 'Detach style'); else detachStyle(kind, target.ids); }
  function stylePop(anchor, kind, target) {
    const cur = linkOfTarget(kind, target), list = styleList(kind), edit = canEdit(), box = h('div', {class: 'hdc-stylepop'}); let handle = null;
    const fromHere = () => { if (target.inst) { const v = vnode(target.inst, target.path); if (!v) return null; if (kind === 'fill') return clone(val(v.n, 'fills') || []); if (kind === 'effect') return clone(val(v.n, 'effects') || []); const o = {}; for (const k of TEXT_KEYS) { const x = val(v.n, k); if (x !== undefined) o[k] = x; } return o; } return styleValueOf(kind, target.ids[0]); };
    const apply = sid => { const s = styles()[sid]; if (!s) return; if (target.inst) setOverride(target.inst, target.path, Object.assign(stylePatch(kind, s.value), {[LINK[kind]]: sid}), 'Apply style'); else applyStyle(sid, target.ids); };
    const make = ibtn('plus', 'New style from this layer', () => { const value = fromHere(); if (value === null) return; let sid = null; if (handle) handle.close();
      S.tx('Create style', () => { sid = createStyle(kind, '', value, target.ids || []); if (sid && target.inst) setOverride(target.inst, target.path, {[LINK[kind]]: sid}, 'Create style'); });
      if (sid) setTimeout(() => styleEditor(anchor, sid, 0), 60); }); make.disabled = !edit;
    box.appendChild(h('div', {class: 'hd-phead'}, h('span', {class: 'hd-ptitle', text: KIND_LABEL[kind] + ' styles'}), make));
    const rows = h('div', {class: 'hdc-picklist', role: 'listbox', 'aria-label': KIND_LABEL[kind] + ' styles'});
    for (const st of list) { const b = h('button', {class: 'hd-mi hdc-pick' + (st.id === cur ? ' cur' : ''), type: 'button', role: 'option', 'aria-selected': String(st.id === cur), 'data-sid': st.id}, stylePreview(st), h('span', {class: 'hd-mlab', text: st.name}), st.id === cur ? icon('check') : null);
      b.disabled = !edit; b.addEventListener('click', () => { if (handle) handle.close(); apply(st.id); });
      rows.appendChild(h('div', {class: 'hdc-srowp'}, b, ibtn('sliders', 'Edit this style', () => styleEditor(anchor, st.id, 0), 'sm'))); }
    if (!list.length) rows.appendChild(h('p', {class: 'hd-note', text: 'No ' + KIND_LABEL[kind].toLowerCase() + ' styles yet. Press + to make one from this layer.'}));
    box.appendChild(rows);
    if (cur && styles()[cur]) { const d = h('button', {class: 'hd-linkbtn', type: 'button', text: 'Detach from \u201C' + styles()[cur].name + '\u201D', on: {click: () => { if (handle) handle.close(); unlinkTarget(kind, target); }}}); d.disabled = !edit; box.appendChild(d); }
    handle = UI.pop(anchor, box, {cls: 'hd-pop-fx hdc-pop', label: KIND_LABEL[kind] + ' styles', side: 'left'});
  }
  const FXT = [['drop', 'Drop shadow'], ['inner', 'Inner shadow'], ['blur', 'Layer blur'], ['bgblur', 'Background blur']];
  function styleEditor(anchor, sid, level) {
    const cur = () => styles()[sid]; if (!cur()) return;
    const kind = cur().kind, edit = canEdit(), body = h('div', {class: 'hdc-styleedit', 'data-sid': sid}), vals = h('div', {class: 'hdc-stylevals'}); let hp = null;
    const value = () => (cur() || {}).value, setValue = (v, g) => updateStyle(sid, {value: v}, g);
    body.appendChild(h('div', {class: 'hd-phead'}, h('span', {class: 'hd-ptitle', text: KIND_LABEL[kind] + ' style'}), ibtn('close', 'Close', () => hp && hp.close())));
    body.appendChild(UI.row(textIn({label: 'Style name', get: () => (cur() || {}).name || '', set: v => { if (v.trim()) updateStyle(sid, {name: v.trim()}); }, max: 80})));
    const draw = () => {
      clear(vals); if (!cur()) return;
      if (kind === 'fill') {
        const list = () => { const a = value(); return Array.isArray(a) ? a : []; };
        paintLines(vals, 'Colour', list, (arr, g) => { const n = list().length; setValue(arr, g); if (arr.length !== n) draw(); }, (level || 0) + 1);
        const add = tbtn('Add a colour', '', () => { setValue(list().concat([{type: 'solid', color: '#D9D9D9', opacity: 1, visible: true}])); draw(); }, 'grow'); add.disabled = !edit; vals.appendChild(UI.row(add));
      } else if (kind === 'text') {
        const tv = k => (value() || {})[k], tset = (k, x, g) => setValue(Object.assign({}, value(), {[k]: x}), g);
        vals.appendChild(UI.row(h('label', {class: 'hd-sfield grow'}, UI.select(UI.fonts.map(f => [f[1], f[1]]), () => tv('font') || 'Inter', x => { UI.loadFont(x); tset('font', x); }, 'Font'))));
        vals.appendChild(UI.row(h('label', {class: 'hd-sfield grow'}, UI.select(WEIGHTS, () => num(tv('fontWeight'), 400), x => tset('fontWeight', x), 'Font weight')),
          UI.numField({label: 'Size', title: 'Font size', min: 1, max: 2000, get: () => num(tv('fontSize'), 16), set: (x, g) => tset('fontSize', x, g)})));
        vals.appendChild(UI.row(UI.numField({icon: 'lh', title: 'Line height (a number, or auto)', min: 0, words: {auto: 'auto', '': 'auto'}, get: () => typeof tv('lineHeight') === 'number' ? tv('lineHeight') : 'auto', set: (x, g) => tset('lineHeight', x, g)}),
          UI.numField({icon: 'ls', title: 'Letter spacing', step: 0.1, min: -100, max: 500, get: () => num(tv('letterSpacing'), 0), set: (x, g) => tset('letterSpacing', x, g)})));
      } else {
        const list = () => { const a = value(); return Array.isArray(a) ? a : []; }, upd = (i, patch, g) => { const a = list().slice(); if (i < a.length) { a[i] = Object.assign({}, a[i], patch); setValue(a, g); } };
        list().forEach((fx, i) => {
          const shadow = fx.type === 'drop' || fx.type === 'inner', f = (k, label, o) => UI.numField(Object.assign({label: label, title: label, get: () => num((list()[i] || {})[k], 0), set: (x, g) => upd(i, {[k]: x}, g)}, o || {}));
          const rm = ibtn('minus', 'Remove this effect', () => { const a = list().slice(); a.splice(i, 1); setValue(a); draw(); }, 'sm'); rm.disabled = !edit;
          vals.appendChild(h('div', {class: 'hd-paint fx'}, h('label', {class: 'hd-sfield grow'}, UI.select(FXT, () => (list()[i] || {}).type, x => { upd(i, x === 'drop' || x === 'inner' ? {type: x, x: num(fx.x, 0), y: num(fx.y, 4), blur: num(fx.blur, 12), spread: num(fx.spread, 0), color: fx.color || '#000000', opacity: fx.opacity === undefined ? 0.25 : fx.opacity} : {type: x, blur: num(fx.blur, 8)}); draw(); }, 'Effect type')), rm));
          if (shadow) { vals.appendChild(UI.row(f('x', 'X'), f('y', 'Y'))); vals.appendChild(UI.row(f('blur', 'Blur', {min: 0}), f('spread', 'Spread')));
            vals.appendChild(UI.colorLine({title: 'Shadow colour', solidOnly: true, hide: false, level: (level || 0) + 1, get: () => ({type: 'solid', color: (list()[i] || {}).color || '#000000', opacity: (list()[i] || {}).opacity === undefined ? 1 : (list()[i] || {}).opacity}), set: (p, g) => upd(i, {color: p.color, opacity: p.opacity}, g)})); }
          else vals.appendChild(UI.row(f('blur', 'Blur', {min: 0, wide: true})));
        });
        const add = tbtn('Add an effect', '', () => { setValue(list().concat(STYLE_NEW.effect())); draw(); }, 'grow'); add.disabled = !edit; vals.appendChild(UI.row(add));
      }
    };
    draw(); body.appendChild(vals);
    const users = styleUsers(sid).length, del = tbtn('Delete', 'Delete this style (the layers keep their look)', () => { if (hp) hp.close(); deleteStyle(sid); }, 'danger'); del.disabled = !edit;
    body.appendChild(h('div', {class: 'hd-row hdc-stylefoot'}, h('span', {class: 'hd-dimtext hd-grow1', text: users === 1 ? 'Used by 1 layer' : 'Used by ' + users + ' layers'}), del));
    hp = UI.pop(anchor, body, {cls: 'hd-pop-fx hdc-pop', label: 'Edit style', side: 'left', level: level || 0});
    const nm = body.querySelector('input'); if (nm && /^(Colour|Text|Effect) \d+$/.test(nm.value)) { nm.focus(); nm.select(); }
  }

  /* ---------------------------------------------------------------- the Variables dialog */
  const dlg = {el: null, grid: null, raf: 0, dirty: false};
  function typeGlyph(type) { return h('span', {class: 'hdc-vtype', title: (VAR_TYPES.find(t => t[0] === type) || ['', ''])[1], 'aria-hidden': 'true'}, type === 'color' ? icon('opacity', 14) : type === 'number' ? '#' : type === 'string' ? icon('text', 14) : icon('check', 14)); }
  function valueCell(v, m) {
    const cur = () => varValue(v.id, m), edit = canEdit(), cell = h('div', {class: 'hdc-vcell', role: 'cell', 'data-var': v.id, 'data-mode': m});
    if (v.type === 'color') {
      const sw = h('button', {class: 'hd-sw big', type: 'button', title: 'Change the colour', 'aria-label': v.name + ', ' + m + ': change the colour'}), hex = h('input', {class: 'hd-in hd-hex', type: 'text', 'aria-label': v.name + ', ' + m + ' hex', spellcheck: 'false', maxlength: '9'}), box = h('div', {class: 'hd-cbox'}, sw, hex);
      const show = () => { const c = String(cur() || '#000000'); sw.style.background = c; if (document.activeElement !== hex) hex.value = c.replace('#', '').toUpperCase(); sw.disabled = hex.disabled = !edit; };
      sw.addEventListener('click', () => UI.paintPicker(box, {solidOnly: true, title: v.name, level: 0, get: () => ({type: 'solid', color: String(cur() || '#000000'), opacity: 1, visible: true}), set: (p, g) => { setVarValue(v.id, m, p.color, g); show(); }}));
      hex.addEventListener('change', () => { const x = hex.value.trim().replace(/^#/, ''); if (/^[0-9a-f]{6}$/i.test(x)) setVarValue(v.id, m, '#' + x.toUpperCase()); else if (/^[0-9a-f]{3}$/i.test(x)) setVarValue(v.id, m, '#' + x.split('').map(c => c + c).join('').toUpperCase()); show(); });
      hex.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); hex.blur(); } });
      show(); cell.appendChild(box);
    } else if (v.type === 'bool') cell.appendChild(switchCtl(() => cur() === true, x => setVarValue(v.id, m, x), v.name + ', ' + m, false));
    else cell.appendChild(textIn({label: v.name + ', ' + m, sync: false, get: () => cur(), set: x => { if (v.type === 'number' && !isFinite(parseFloat(x))) { UI.toast('That is not a number.'); return; } setVarValue(v.id, m, v.type === 'number' ? parseFloat(x) : x); }, max: 2000}));
    return cell;
  }
  function drawVars() {
    if (!dlg.el || !document.contains(dlg.el)) { dlg.el = null; return; }
    const grid = dlg.grid, list = modes(), all = varList(), edit = canEdit();
    clear(grid); grid.style.gridTemplateColumns = 'minmax(170px,1.3fr) repeat(' + list.length + ', minmax(120px,1fr)) 30px'; grid.style.minWidth = (220 + list.length * 128) + 'px';
    grid.appendChild(h('div', {class: 'hdc-vh', role: 'columnheader', text: 'Name'}));
    for (const m of list) { const rm = list.length > 1 ? ibtn('minus', 'Delete the mode ' + m, () => { deleteMode(m); drawVars(); }, 'sm') : null; if (rm) rm.disabled = !edit;
      grid.appendChild(h('div', {class: 'hdc-vh hdc-vmode', role: 'columnheader'}, textIn({label: 'Mode name', sync: false, cls: 'hdc-strong', get: () => m, set: x => { renameMode(m, x); drawVars(); }, max: 60}), rm)); }
    grid.appendChild(h('div', {class: 'hdc-vh'}));
    if (!all.length) grid.appendChild(h('p', {class: 'hd-note hdc-vempty', text: 'No variables yet. A variable is a colour, a number, a text or a switch with a name: bind it to layers, and give it one value per mode (for example Light and Dark).'}));
    let group = null;
    for (const v of all) {
      const cut = v.name.lastIndexOf('/'), g = cut > 0 ? v.name.slice(0, cut) : '';
      if (g !== group) { group = g; if (g) grid.appendChild(h('div', {class: 'hdc-vgroup', text: g})); }
      grid.appendChild(h('div', {class: 'hdc-vname', role: 'rowheader', 'data-var': v.id}, typeGlyph(v.type), textIn({label: 'Variable name', sync: false, get: () => v.name, set: x => { renameVar(v.id, x); drawVars(); }, max: 120})));
      for (const m of list) grid.appendChild(valueCell(v, m));
      const rm = ibtn('trash', 'Delete the variable ' + v.name, () => { deleteVar(v.id); drawVars(); }, 'sm'); rm.disabled = !edit; grid.appendChild(h('div', {class: 'hdc-vdel'}, rm));
    }
  }
  function varsChanged() {
    if (!dlg.el) return; if (!document.contains(dlg.el)) { dlg.el = null; return; }
    const a = document.activeElement;
    if (a && typing(a) && dlg.grid.contains(a)) { if (!dlg.dirty) { dlg.dirty = true; dlg.grid.addEventListener('focusout', () => { dlg.dirty = false; setTimeout(drawVars, 0); }, {once: true}); } return; }
    if (document.querySelector('.hd-pop-picker')) return;                     /* a colour is being picked: the cell shows it itself */
    if (!dlg.raf) dlg.raf = requestAnimationFrame(() => { dlg.raf = 0; drawVars(); });
  }
  function openVariables() {
    const grid = h('div', {class: 'hdc-vgrid', role: 'table', 'aria-label': 'Variables'}), edit = canEdit();
    const addB = h('button', {class: 'hd-btn pri', type: 'button', title: 'New variable'}, icon('plus', 14), h('span', {text: 'Variable'}));
    addB.addEventListener('click', () => UI.menu(addB, VAR_TYPES.map(t => ({label: t[1], run: () => { const id = addVar(t[0]); drawVars(); const inp = id && grid.querySelector('.hdc-vname[data-var="' + id + '"] input'); if (inp) { inp.focus(); inp.select(); } }})), {label: 'New variable'}));
    const modeB = h('button', {class: 'hd-btn', type: 'button', title: 'Add a mode (a second set of values)'}, icon('plus', 14), h('span', {text: 'Mode'}));
    modeB.addEventListener('click', () => { if (!varList().length) { UI.toast('Make a variable first.'); return; } addMode(); drawVars(); });
    addB.disabled = modeB.disabled = !edit;
    const head = h('div', {class: 'hd-sheethead'}, h('h2', {text: 'Variables'}), h('div', {class: 'hdc-vacts'}, addB, modeB, ibtn('close', 'Close', () => UI.closeModal())));
    dlg.el = UI.modal('hdc-vars', 'Variables', [head, h('div', {class: 'hdc-vscroll'}, grid), h('p', {class: 'hd-note hdc-vfoot', text: 'A "/" in a name makes a group (colour/brand). Bind a variable to a layer in the Variables section of the Design panel; a frame can pick the mode for everything inside it.'})]);
    dlg.grid = grid; drawVars();
  }

  /* ---------------------------------------------------------------- the library: components of the tenant's other files */
  function docKids(doc) {
    const m = {}, nodes = doc.nodes || {};
    for (const id in nodes) { const p = nodes[id] && nodes[id].parent; if (p) (m[p] = m[p] || []).push(id); }
    for (const p in m) m[p].sort((a, b) => { const x = String(nodes[a].idx || ''), y = String(nodes[b].idx || ''); return x < y ? -1 : x > y ? 1 : a < b ? -1 : a > b ? 1 : 0; });
    return m;
  }
  function subtreeIds(kids, id, out) { out.push(id); const ks = kids[id] || []; for (let i = 0; i < ks.length; i++) subtreeIds(kids, ks[i], out); return out; }
  const LIB_DROP = {parent: 1, idx: 1, type: 1, fillStyle: 1, textStyle: 1, effectStyle: 1, bind: 1, mode: 1, reactions: 1, protoStart: 1, libSrc: 1, libHash: 1, libId: 1, locked: 1};
  function libHashOf(doc, kids, id) {
    return hash(JSON.stringify(subtreeIds(kids, id, []).map(i => { const n = doc.nodes[i], o = {}; for (const k of Object.keys(n).sort()) if (!(i === id && (k === 'x' || k === 'y' || k === 'parent' || k === 'idx'))) o[k] = n[k]; return [i, o]; })));
  }
  /* what a file offers: [{id, kind, name, w, h, variants}] */
  function libComponents(doc) {
    const nodes = (doc && doc.nodes) || {}, kids = docKids(doc || {}), out = [];
    for (const id in nodes) { const n = nodes[id]; if (!n) continue; const pt = nodes[n.parent] ? nodes[n.parent].type : '';
      if (n.type === 'COMPONENT_SET') { const vs = (kids[id] || []).filter(k => nodes[k].type === 'COMPONENT'); if (vs.length) out.push({id: id, kind: 'set', name: n.name || 'Component set', w: W(n), h: H(n), variants: vs.length}); }
      else if (n.type === 'COMPONENT' && pt !== 'COMPONENT_SET') out.push({id: id, kind: 'component', name: n.name || 'Component', w: W(n), h: H(n), variants: 1}); }
    return out.sort((a, b) => a.name.toLowerCase() < b.name.toLowerCase() ? -1 : 1);
  }
  function localImports() { const m = new Map(); S.walk(ROOT, (id, n) => { if ((n.type === 'COMPONENT' || n.type === 'COMPONENT_SET') && n.libSrc && n.libSrc.file && n.libSrc.id) { m.set(n.libSrc.file + ':' + n.libSrc.id, id); return false; } return n.type === 'INSTANCE' ? false : undefined; }); return m; }
  /* copy (or bring up to date) components of another file into this one, with the components their nested instances need.
     file = {id, name}; srcIds = COMPONENT / COMPONENT_SET ids in doc; at = [world x, world y] | null.  ->  local ids */
  function syncFromLibrary(file, doc, srcIds, at) {
    if (!guard() || !doc || !doc.nodes) return [];
    const nodes = doc.nodes, kids = docKids(doc), order = [], seen = new Set();
    const rootOf = id => { const n = nodes[id]; if (!n) return null; if (n.type === 'COMPONENT' && nodes[n.parent] && nodes[n.parent].type === 'COMPONENT_SET') return n.parent; return n.type === 'COMPONENT' || n.type === 'COMPONENT_SET' ? id : null; };
    const visit = id => { const r = rootOf(id); if (!r || seen.has(r)) return; seen.add(r);
      for (const k of subtreeIds(kids, r, [])) { const n = nodes[k]; if (n.type !== 'INSTANCE') continue; if (n.comp) visit(n.comp); if (n.ov && typeof n.ov === 'object') for (const p in n.ov) if (n.ov[p] && n.ov[p].comp) visit(n.ov[p].comp); }
      order.push(r); };
    for (const id of srcIds) visit(id);
    if (!order.length) return [];
    const have = localImports(), idMap = {}, made = new Set(), out = [];
    S.tx(order.some(r => !have.has(file.id + ':' + r)) ? 'Add from library' : 'Update from library', () => {
      const pb = S.worldBounds(HD.sel.page); let px = at ? at[0] : (pb.w || pb.h ? pb.x + pb.w + 80 : 0), py = at ? at[1] : (pb.w || pb.h ? pb.y : 0);
      const plan = [];
      for (const r of order) {                                     /* 1: every node exists (parents first) */
        const src = nodes[r], ids = subtreeIds(kids, r, []); let local = have.get(file.id + ':' + r);
        if (!local || !S.has(local)) { local = S.create(src.type, HD.sel.page, {name: src.name || 'Component', x: Math.round(at && r === rootOf(srcIds[0]) ? px - W(src) / 2 : px), y: Math.round(at && r === rootOf(srcIds[0]) ? py - H(src) / 2 : py), w: W(src), h: H(src)}); made.add(local); py += H(src) + 40; }
        const byLib = new Map(); S.walk(local, (id, n) => { if (id !== local && n.libId) byLib.set(n.libId, id); });
        idMap[r] = local;
        for (const sid of ids.slice(1)) { const sn = nodes[sid]; let lid = byLib.get(sid); if (!lid) lid = S.create(sn.type, idMap[sn.parent], {name: sn.name || ''}); byLib.delete(sid); idMap[sid] = lid; }
        plan.push({r: r, local: local, ids: ids, stale: Array.from(byLib.values())});
      }
      for (const p of plan) {                                      /* 2: every node gets the source's properties */
        for (const sid of p.ids) {
          const sn = nodes[sid], lid = idMap[sid], ln = S.get(lid), isRoot = sid === p.r, want = {}; if (!ln) continue;
          for (const k in sn) if (!LIB_DROP[k] && !(isRoot && (k === 'x' || k === 'y'))) want[k] = sn[k];
          if (want.comp && idMap[want.comp]) want.comp = idMap[want.comp];
          if (want.ov && typeof want.ov === 'object') { const o = {}; for (const k in want.ov) { const e = Object.assign({}, want.ov[k]); if (e.comp && idMap[e.comp]) e.comp = idMap[e.comp]; delete e.fillStyle; delete e.textStyle; delete e.effectStyle; o[remapPath(k, idMap)] = e; } want.ov = o; }
          if (Array.isArray(want.cprops)) want.cprops = want.cprops.map(c => Object.assign({}, c, {target: remapPath(c.target, idMap)}));
          if (isRoot) { want.libSrc = {file: file.id, id: sid, name: String(file.name || 'another file').slice(0, 80)}; want.libHash = libHashOf(doc, kids, sid); } else want.libId = sid;
          const patch = {};
          for (const k in want) if (!same(ln[k], want[k])) patch[k] = want[k];
          for (const k in ln) if (want[k] === undefined && !LIB_DROP[k] && !(isRoot && (k === 'x' || k === 'y')) && k !== 'name') patch[k] = null;
          if (ln.type !== sn.type) patch.type = sn.type;
          if (!isRoot && (ln.parent !== idMap[sn.parent] || ln.idx !== sn.idx)) { patch.parent = idMap[sn.parent]; if (typeof sn.idx === 'string' && sn.idx) patch.idx = sn.idx; }
          if (Object.keys(patch).length) S.set(lid, patch);
        }
        if (p.stale.length) S.remove(p.stale.filter(id => S.has(id)));
      }
      for (const id of srcIds) { const r = rootOf(id); if (r && idMap[r]) out.push(idMap[r]); }
    });
    return out;
  }
  const libDocs = new Map();
  function fetchDoc(fileId, fresh) {
    if (!fresh && libDocs.has(fileId)) return Promise.resolve(libDocs.get(fileId));
    return UI.api('GET', '/files/' + encodeURIComponent(fileId) + '/doc').then(d => { const doc = (d && d.doc) || {nodes: {}}; libDocs.set(fileId, doc); return doc; });
  }
  /* which local library components differ from their source right now: Map(local id -> 'changed' | 'gone') */
  async function checkLibrary() {
    const byFile = new Map(), res = new Map();
    S.walk(ROOT, (id, n) => { if ((n.type === 'COMPONENT' || n.type === 'COMPONENT_SET') && n.libSrc && n.libSrc.file) { if (!byFile.has(n.libSrc.file)) byFile.set(n.libSrc.file, []); byFile.get(n.libSrc.file).push(id); return false; } return n.type === 'INSTANCE' ? false : undefined; });
    for (const entry of byFile) { let doc; try { doc = await fetchDoc(entry[0], true); } catch (e) { for (const id of entry[1]) res.set(id, 'gone'); continue; }
      const kids = docKids(doc); for (const id of entry[1]) { const n = S.get(id); if (!n) continue; if (!doc.nodes[n.libSrc.id]) res.set(id, 'gone'); else if (libHashOf(doc, kids, n.libSrc.id) !== n.libHash) res.set(id, 'changed'); } }
    return res;
  }
  async function updateFromLibrary(localIds) {
    if (!guard()) return 0; let done = 0; const groups = new Map();
    for (const id of [].concat(localIds)) { const n = S.get(id); if (n && n.libSrc && n.libSrc.file) { if (!groups.has(n.libSrc.file)) groups.set(n.libSrc.file, {name: n.libSrc.name, ids: []}); groups.get(n.libSrc.file).ids.push(n.libSrc.id); } }
    for (const entry of groups) {
      let doc; try { doc = await fetchDoc(entry[0], true); } catch (e) { UI.toast('The library file could not be read: ' + (e.message || 'no answer'), true); continue; }
      const kids = docKids(doc), want = entry[1].ids.filter(sid => doc.nodes[sid]), have = localImports();
      const changed = want.filter(sid => { const l = S.get(have.get(entry[0] + ':' + sid)); return !l || l.libHash !== libHashOf(doc, kids, sid); });
      if (want.length < entry[1].ids.length) UI.toast('A component is no longer in its library file. Your copy stays as it is.');
      if (changed.length) { syncFromLibrary({id: entry[0], name: entry[1].name}, doc, changed, null); done += changed.length; }
    }
    UI.toast(done ? (done === 1 ? 'The component was updated from the library.' : done + ' components were updated from the library.') : 'Already up to date.');
    assets.updates = null; assets.sig = ''; UI.refresh();
    return done;
  }

  /* ---------------------------------------------------------------- the Assets panel (left) */
  const assets = {el: null, q: '', sig: '', timer: 0, local: null, libBody: null, updates: null, lib: {files: null, loading: false, error: '', open: null, opening: false}};
  function dragCard(ev, compId, card) {
    if (ev.button !== 0 || !canEdit()) return;
    const sx = ev.clientX, sy = ev.clientY; let ghost = null;
    const mv = e => {
      if (!ghost) { if (Math.hypot(e.clientX - sx, e.clientY - sy) < 5) return; ghost = h('div', {class: 'hdc-ghost', 'aria-hidden': 'true'}, thumb(compId, 140, 100)); document.body.appendChild(ghost); document.body.classList.add('hdc-dragging'); }
      ghost.style.left = e.clientX + 'px'; ghost.style.top = e.clientY + 'px';
    };
    const end = e => {
      window.removeEventListener('pointermove', mv, true); window.removeEventListener('pointerup', end, true); window.removeEventListener('pointercancel', end, true);
      if (!ghost) return; ghost.remove(); document.body.classList.remove('hdc-dragging'); card.dataset.dragged = '1'; setTimeout(() => { delete card.dataset.dragged; }, 0);
      if (e.type !== 'pointerup' || !T.canvas) return;
      const r = T.canvas.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) return;
      const w = HD.render.screenToWorld(e.clientX - r.left, e.clientY - r.top); if (insertAt(compId, w[0], w[1])) T.canvas.focus({preventScroll: true});
    };
    window.addEventListener('pointermove', mv, true); window.addEventListener('pointerup', end, true); window.addEventListener('pointercancel', end, true);
  }
  function insertCentre(compId) { const c = T.view.centre(), w = HD.render.screenToWorld(c[0], c[1]); return insertAt(compId, w[0], w[1]); }
  function drawLocal() {
    const box = assets.local; if (!box) return; clear(box);
    const q = assets.q.trim().toLowerCase(), all = listComponents(), list = all.filter(c => !q || c.name.toLowerCase().indexOf(q) >= 0);
    if (!list.length) { box.appendChild(h('p', {class: 'hd-note hdc-anote', text: all.length ? 'No component with that name.' : 'No components yet. Select layers and press ' + UI.keysLabel('mod+alt+k') + ' to turn them into a component you can reuse.'})); return; }
    for (const c of list.slice(0, 120)) {
      const card = h('button', {class: 'hdc-card', type: 'button', title: c.name + ': drag onto the canvas to place an instance', 'data-id': c.id, 'data-comp': c.first},
        h('span', {class: 'hdc-cardth'}, thumb(c.first, 92, 60)), h('span', {class: 'hdc-cardname', text: c.name}), c.kind === 'set' ? h('span', {class: 'hdc-cardsub', text: c.variants.length + (c.variants.length === 1 ? ' variant' : ' variants')}) : null);
      card.addEventListener('pointerdown', ev => dragCard(ev, c.first, card));
      card.addEventListener('click', () => { if (card.dataset.dragged) return; UI.menu(card, [{label: 'Place an instance', icon: 'instance', disabled: !canEdit(), run: () => insertCentre(c.first)}, {label: 'Go to main component', icon: 'component', run: () => { const pg = S.pageOf(c.id); if (pg && pg !== HD.sel.page) UI.setPage(pg); HD.sel.set([c.id]); T.view.fit([c.id]); }}], {label: c.name}); });
      box.appendChild(card);
    }
    if (list.length > 120) box.appendChild(h('p', {class: 'hd-note hdc-anote', text: 'Showing the first 120. Search to find the others.'}));
  }
  async function loadLibFiles() {
    const L = assets.lib; if (L.loading) return; L.loading = true; L.error = ''; drawLib();
    try { const d = await UI.api('GET', '/files'), mine = HD.app && HD.app.file && HD.app.file.id; L.files = ((d && d.files) || []).filter(f => f && f.id !== mine && !f.trashed).slice(0, 200); }
    catch (e) { L.error = e.message || 'The files could not be listed.'; }
    L.loading = false; drawLib();
  }
  async function openLibFile(f) {
    const L = assets.lib; if (L.open === f.id) { L.open = null; drawLib(); return; }
    L.open = f.id; L.opening = true; drawLib();
    try { await fetchDoc(f.id, true); } catch (e) { L.error = e.message || 'That file could not be read.'; L.open = null; }
    L.opening = false; drawLib();
  }
  function drawLib() {
    const b = assets.libBody, L = assets.lib; if (!b) return; clear(b);
    const imports = localImports(), edit = canEdit();
    if (!L.files) { b.appendChild(h('p', {class: 'hd-note', text: 'Components of your other design files. Adding one puts a copy into this file.'}));
      const go = tbtn(L.loading ? 'Loading\u2026' : 'Browse your files', '', loadLibFiles, 'grow'); go.disabled = L.loading; b.appendChild(UI.row(go)); }
    else if (!L.files.length) b.appendChild(h('p', {class: 'hd-note', text: 'You have no other design files yet.'}));
    else for (const f of L.files) {
      const open = L.open === f.id, fb = h('button', {class: 'hdc-libfile' + (open ? ' open' : ''), type: 'button', 'aria-expanded': String(open), 'data-file': f.id}, h('span', {class: 'hd-lcaret' + (open ? ' open' : '')}, icon('right', 10)), h('span', {class: 'hd-ltype'}, icon('page', 14)), h('span', {class: 'hd-lname', text: f.name || 'Untitled'}));
      fb.addEventListener('click', () => openLibFile(f)); b.appendChild(fb);
      if (!open) continue;
      const doc = libDocs.get(f.id), items = h('div', {class: 'hdc-libitems'}); b.appendChild(items);
      if (L.opening || !doc) { items.appendChild(h('p', {class: 'hd-note', text: 'Loading\u2026'})); continue; }
      const comps = libComponents(doc); if (!comps.length) { items.appendChild(h('p', {class: 'hd-note', text: 'This file has no components.'})); continue; }
      for (const c of comps.slice(0, 200)) { const has = imports.has(f.id + ':' + c.id);
        const add = tbtn(has ? 'Added' : 'Add', has ? 'Already in this file: place an instance' : 'Copy this component into this file', () => { if (has) { const l = S.get(imports.get(f.id + ':' + c.id)); if (l) insertCentre(l.type === 'COMPONENT_SET' ? S.children(imports.get(f.id + ':' + c.id)).filter(isMain)[0] : imports.get(f.id + ':' + c.id)); return; }
          const ids = syncFromLibrary({id: f.id, name: f.name}, doc, [c.id], null); if (ids.length) { HD.sel.set([ids[0]]); T.view.fit([ids[0]]); UI.toast('\u201C' + c.name + '\u201D is now a component of this file.'); } assets.sig = ''; UI.refresh(); }); add.disabled = !edit;
        items.appendChild(h('div', {class: 'hdc-librow', 'data-src': c.id}, h('span', {class: 'hd-ltype'}, icon('component', 14)), h('span', {class: 'hd-lname', text: c.name}), h('span', {class: 'hd-count', text: c.kind === 'set' ? c.variants + ' variants' : Math.round(c.w) + ' \u00D7 ' + Math.round(c.h)}), add)); }
    }
    if (L.error) b.appendChild(h('p', {class: 'hd-note hdc-bad', role: 'alert', text: L.error}));
    if (imports.size) {
      const up = assets.updates, n = up ? up.size : 0, chk = tbtn(up ? (n ? 'Update ' + (n === 1 ? '1 component' : n + ' components') : 'Check again') : 'Check for updates', 'Compare the copies in this file with their library files', async () => {
        if (up && n) { await updateFromLibrary(Array.from(up.keys()).filter(id => up.get(id) === 'changed')); return; }
        chk.disabled = true; try { assets.updates = await checkLibrary(); } catch (e) { UI.toast(e.message || 'The check failed.', true); } const m = assets.updates ? assets.updates.size : 0; UI.toast(m ? (m === 1 ? '1 library component has changed.' : m + ' library components have changed.') : 'Every library component is up to date.'); drawLib(); }, 'grow'); chk.disabled = !edit;
      b.appendChild(h('div', {class: 'hdc-sublab', text: imports.size === 1 ? '1 component here came from the library' : imports.size + ' components here came from the library'})); b.appendChild(UI.row(chk));
    }
  }
  function syncAssets() {
    if (!assets.el) return; const sig = assets.q + '\u0001' + ver; if (sig === assets.sig) return;
    const first = !assets.sig || assets.sig.split('\u0001')[0] !== assets.q; assets.sig = sig;
    clearTimeout(assets.timer);
    if (first) { drawLocal(); drawLib(); } else assets.timer = setTimeout(() => { if (assets.el && document.contains(assets.el)) { drawLocal(); drawLib(); } }, 280);
  }
  function assetsRender(el) {
    if (assets.el !== el || !el.firstChild) {
      clear(el); assets.el = el; assets.sig = '';
      const q = h('input', {class: 'hd-in hd-search', type: 'search', placeholder: 'Search components', 'aria-label': 'Search components', value: assets.q});
      q.addEventListener('input', () => { assets.q = q.value; assets.sig = ''; syncAssets(); });
      const wrap = h('div', {class: 'hdc-assets'}, h('div', {class: 'hdc-ahead'}, q)); el.appendChild(wrap);
      const a = UI.section(wrap, 'This file', null, {cls: 'hdc-asec'}); assets.local = h('div', {class: 'hdc-agrid'}); a.body.appendChild(assets.local);
      const l = UI.section(wrap, 'Library', null, {cls: 'hdc-asec'}); assets.libBody = h('div', {class: 'hdc-lib'}); l.body.appendChild(assets.libBody);
    }
    syncAssets();
  }
  function showAssets() { UI.state.leftTab = 'assets'; if (UI.state.leftTabs) UI.state.leftTabs.dataset.sig = ''; UI.refresh(); setTimeout(() => { const q = assets.el && assets.el.querySelector('input'); if (q) q.focus(); }, 60); }
  UI.registerPanel('left', 'assets', {title: 'Assets', render: assetsRender});

  /* ---------------------------------------------------------------- menus, commands, shortcuts */
  const NO_COMP = {COMPONENT: 1, COMPONENT_SET: 1};
  UI.registerMenu('context', ids => canEdit() && ids.length && !ids.some(id => NO_COMP[typeOf(id)] || hasAncestorOfType(id, NO_COMP)) ? {label: 'Create a component', icon: 'component', keys: 'mod+alt+k', run: createComponent} : null);
  UI.registerMenu('context', ids => canEdit() && ids.length && ids.every(standalone) ? {label: 'Combine as variants', run: () => combineAsVariants(ids)} : null);
  UI.registerMenu('context', ids => ids.length === 1 && typeOf(ids[0]) === 'INSTANCE' ? {label: 'Go to main component', disabled: !mainOf(ids[0]), run: () => goToMain(ids[0])} : null);
  UI.registerMenu('context', ids => canEdit() && ids.length && ids.every(id => typeOf(id) === 'INSTANCE') && ids.some(id => listOverrides(id).length) ? {label: 'Reset all changes', run: () => resetAll(ids)} : null);
  UI.registerMenu('context', ids => canEdit() && ids.length && ids.every(id => typeOf(id) === 'INSTANCE') ? {label: 'Detach instance', keys: 'mod+alt+b', run: () => detach(ids)} : null);
  UI.registerMenu('main', {label: 'Variables\u2026', icon: 'sliders', run: () => openVariables()});
  /* commands are added once the editor is up: the first-wave command list is only filled when it is still empty */
  let cmdTimer = setInterval(() => {
    if (!UI.mounted) return; clearInterval(cmdTimer); cmdTimer = 0;
    const ed = (id, label, keys, run) => UI.command({id: 'comp.' + id, label: label, group: 'Components', keys: keys, run: run, edit: true});
    ed('create', 'Create a component', 'mod+alt+k', createComponent); ed('detach', 'Detach instance', 'mod+alt+b', () => detach());
    ed('combine', 'Combine as variants', null, () => combineAsVariants()); ed('reset', 'Reset all changes of the instance', null, () => resetAll(selIds()));
    ed('applyVars', 'Apply the variables again', null, resolveAll);
    UI.command({id: 'comp.main', label: 'Go to main component', group: 'Components', run: () => { const id = selIds()[0]; if (id && typeOf(id) === 'INSTANCE') goToMain(id); }});
    UI.command({id: 'comp.assets', label: 'Show the assets', group: 'Components', keys: 'alt+2', run: showAssets});
    UI.command({id: 'comp.vars', label: 'Variables\u2026', group: 'Components', run: () => openVariables()});
  }, 120);

  /* ---------------------------------------------------------------- following the document */
  S.on('change', ch => {
    ver++;
    if (!ch || !ch.ids) { structVer++; rootVer++; return; }
    if (ch.ids.has(ROOT)) { rootVer++; varsChanged(); }
    let st = ch.structural !== false || !ch.props;
    if (!st) ch.props.forEach(ps => { if (!st && ps && typeof ps.has === 'function' && (ps.has('name') || ps.has('cprops') || ps.has('type') || ps.has('comp') || ps.has('libSrc'))) st = true; });
    if (st) structVer++;
  });
  S.on('load', () => { ver++; structVer++; rootVer++; treeCache.clear(); sub.inst = null; sub.path = ''; assets.sig = ''; assets.updates = null; });

  HD.comp = {
    /* instances */
    vtree: vtree, vnode: vnode, hitChain: hitChain, createComponent: createComponent, createInstance: createInstance, insertAt: insertAt, detach: detach, goToMain: goToMain, swap: swap,
    setOverride: setOverride, resetOverride: resetOverride, resetAll: resetAll, listOverrides: listOverrides, isOverridden: isOverridden, baseValue: baseValue, listComponents: listComponents, instancesOf: instancesOf,
    sub: sub, select: setSub, deselect: clearSub,
    /* variants + component properties */
    combineAsVariants: combineAsVariants, setInfo: setInfo, variantInfo: variantInfo, setVariant: setVariant, addVariant: addVariant, addVariantProp: addVariantProp, removeVariantProp: removeVariantProp,
    renameVariantProp: renameVariantProp, renameVariantValue: renameVariantValue, parseVariant: parseVariant,
    cprops: cpropsOf, addProp: addCprop, updateProp: updateCprop, removeProp: removeCprop, propValue: cpropValue, setProp: setCprop,
    /* styles */
    styles: styleList, createStyle: createStyle, applyStyle: applyStyle, updateStyle: updateStyle, deleteStyle: deleteStyle, detachStyle: detachStyle, styleUsers: styleUsers, styleValueOf: styleValueOf,
    /* variables */
    vars: varList, modes: modes, addVar: addVar, renameVar: renameVar, setVarValue: setVarValue, deleteVar: deleteVar, addMode: addMode, renameMode: renameMode, deleteMode: deleteMode,
    bind: bind, bindsOf: id => bindsOf(S.get(id)), setMode: setMode, modeOf: modeOf, varValue: varValue, resolveAll: resolveAll, openVariables: openVariables,
    /* assets + library */
    showAssets: showAssets, libComponents: libComponents, syncFromLibrary: syncFromLibrary, checkLibrary: checkLibrary, updateFromLibrary: updateFromLibrary
  };
})();

/* HOOLA DESIGN - D2 design depth (docs/HOOLA_DESIGN_PLAN.md, phase D2). Loaded after hd-ui.js.
   HD.vector
     edit(id) / leave() / editing      vector edit mode: the anchor points and curve handles of a VECTOR, on the canvas
     toVector(id)                      a RECT / ELLIPSE / POLYGON / STAR / LINE becomes a VECTOR with the same outline
     editShape()                       "Edit shape": convert when needed, then edit
     bool(op)                          union | subtract | intersect | exclude: a GROUP with `bool` (the renderer draws the result)
     flatten()                         a boolean group / a shape / several shapes -> ONE VECTOR
     mask()                            "Use as mask" / "Remove mask"
     rulers, grids (true / false)      rulers + guides (Shift+R), layout grids (Shift+G)
     model: toModel(segs) toD(subs)    the path model (for tests and other files)
   Also here: guides pulled out of the rulers (PAGE `guides`), snapping to them, the "Layout grid" and "Combine"
   sections of the Design panel, on-canvas handles for the gradient open in the colour picker, and the red distance
   lines shown while Alt is held over another layer.
   Path geometry (parsing, outlines, the boolean engine) lives in hd-render.js (HD.render.geom): one copy, used by both.
   Every edit is an HD.store transaction; a whole drag is one undo step. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const DEG = Math.PI / 180, TAU = Math.PI * 2;
  const ACC = '#6E55F0', RED = '#F0447C', MEASURE = '#E5484D';
  const S = () => HD.store, R = () => HD.render, TL = () => HD.tools, U = () => HD.tools.u, GEO = () => HD.render.geom, MX = () => HD.math;
  function num(v, d) { return typeof v === 'number' && v === v && v !== Infinity && v !== -Infinity ? v : d; }
  function r2(v) { return Math.round(v * 100) / 100; }
  function fmt(v) { v = Math.round(v * 100) / 100; return String(Object.is(v, -0) ? 0 : v); }
  function P(id, name) { return S().prop(id, name); }
  function typeOf(id) { const n = S().get(id); return n ? n.type : ''; }
  function toast(msg, bad) { if (HD.ui && HD.ui.toast) HD.ui.toast(msg, bad); }
  function canEdit() { try { return U().canEdit(); } catch (e) { return false; } }
  function guard() { if (!canEdit()) { toast('This file is view only.'); return false; } return true; }
  function redraw() { if (HD.render && HD.render.invalidate) HD.render.invalidate(); }
  function panel() { if (HD.ui && HD.ui.state) { HD.ui.state.sig = ''; HD.ui.refresh(); } }
  function pref(key, def) { try { const v = localStorage.getItem('hoola.design.' + key); return v === null ? def : v === '1'; } catch (e) { return def; } }
  function setPref(key, on) { try { localStorage.setItem('hoola.design.' + key, on ? '1' : '0'); } catch (e) { /* private mode */ } }
  function w2s(x, y) { return R().worldToScreen(x, y); }
  function zoom() { return (R().view && R().view.zoom) || 1; }
  function isBool(n) { return !!n && n.type === 'GROUP' && (n.bool === 'union' || n.bool === 'subtract' || n.bool === 'intersect' || n.bool === 'exclude'); }

  /* ================================================================== the path model
     subs = [{closed, pts: [{x, y, i, o, sm}]}]: i / o = the curve handle before / after the point ([x, y], or null
     for a straight side); sm = the two handles are kept in one line (a smooth point). */
  function isSmooth(p) {
    if (!p.i || !p.o) return false;
    const ax = p.x - p.i[0], ay = p.y - p.i[1], bx = p.o[0] - p.x, by = p.o[1] - p.y, la = Math.hypot(ax, ay), lb = Math.hypot(bx, by);
    return la > 1e-6 && lb > 1e-6 && Math.abs(ax * by - ay * bx) <= 0.02 * la * lb && ax * bx + ay * by > 0;
  }
  function toModel(segs) {
    const subs = [];
    let cur = null, start = null;
    const same = (ax, ay, bx, by) => Math.abs(ax - bx) < 1e-6 && Math.abs(ay - by) < 1e-6;
    const end = () => {
      if (cur && cur.pts.length) {
        if (cur.closed && cur.pts.length > 1) { const a = cur.pts[0], b = cur.pts[cur.pts.length - 1]; if (same(a.x, a.y, b.x, b.y)) { if (b.i) a.i = b.i; cur.pts.pop(); } }
        subs.push(cur);
      }
      cur = null;
    };
    const open = () => { if (!cur && start) cur = {closed: false, pts: [{x: start[0], y: start[1], i: null, o: null, sm: false}]}; return cur; };
    for (const sg of segs || []) {
      if (sg[0] === 'M') { end(); start = [sg[1], sg[2]]; cur = {closed: false, pts: [{x: sg[1], y: sg[2], i: null, o: null, sm: false}]}; }
      else if (sg[0] === 'L') { if (open()) cur.pts.push({x: sg[1], y: sg[2], i: null, o: null, sm: false}); }
      else if (sg[0] === 'C') {
        if (!open()) continue;
        const p = cur.pts[cur.pts.length - 1], q = {x: sg[5], y: sg[6], i: null, o: null, sm: false};
        if (!same(sg[1], sg[2], p.x, p.y)) p.o = [sg[1], sg[2]];
        if (!same(sg[3], sg[4], q.x, q.y)) q.i = [sg[3], sg[4]];
        cur.pts.push(q);
      } else if (sg[0] === 'Z') { if (cur) { cur.closed = true; end(); } }
    }
    end();
    for (const s of subs) for (const p of s.pts) p.sm = isSmooth(p);
    return subs;
  }
  function toD(subs, dx, dy) {
    dx = dx || 0; dy = dy || 0;
    const f = (v) => { v = Math.round(v * 100) / 100; return Object.is(v, -0) ? '0' : String(v); };
    let d = '';
    for (const s of subs) {
      const n = s.pts.length;
      if (!n) continue;
      const seg = (a, b, last) => {
        if (a.o || b.i) { const c1 = a.o || [a.x, a.y], c2 = b.i || [b.x, b.y]; d += 'C' + f(c1[0] + dx) + ' ' + f(c1[1] + dy) + ' ' + f(c2[0] + dx) + ' ' + f(c2[1] + dy) + ' ' + f(b.x + dx) + ' ' + f(b.y + dy); }
        else if (!last) d += 'L' + f(b.x + dx) + ' ' + f(b.y + dy);
      };
      d += 'M' + f(s.pts[0].x + dx) + ' ' + f(s.pts[0].y + dy);
      for (let i = 1; i < n; i++) seg(s.pts[i - 1], s.pts[i], false);
      if (s.closed) { if (n > 1) seg(s.pts[n - 1], s.pts[0], true); d += 'Z'; }
    }
    return d;
  }
  function cloneSubs(subs) { return subs.map(s => ({closed: s.closed, pts: s.pts.map(p => ({x: p.x, y: p.y, i: p.i ? [p.i[0], p.i[1]] : null, o: p.o ? [p.o[0], p.o[1]] : null, sm: p.sm}))})); }
  function shiftSegs(segs, dx, dy) { for (const sg of segs) for (let i = 1; i < sg.length; i += 2) { sg[i] += dx; sg[i + 1] += dy; } return segs; }

  /* ================================================================== boxes that hug a path
     f = the node's geometry frozen at some moment: {x, y, w, h, rot, fh, fv}. frameMat(f) = its matrix into the
     parent's space; rebox(f, b) = the box (same turn / flips) that hugs bounds b of that frame without anything
     moving on the canvas. */
  function frameOf(n) { return {x: num(n.x, 0), y: num(n.y, 0), w: num(n.w, 100), h: n.type === 'LINE' ? 0 : num(n.h, 100), rot: num(n.rot, 0), fh: n.flipH === true, fv: n.flipV === true}; }
  function linOf(f) { const r = f.rot * DEG, cs = Math.cos(r), sn = Math.sin(r); return [f.fh ? -cs : cs, f.fh ? -sn : sn, f.fv ? sn : -sn, f.fv ? -cs : cs]; }
  function frameMat(f) { const l = linOf(f), cx = f.w / 2, cy = f.h / 2; return [l[0], l[1], l[2], l[3], f.x + cx - (l[0] * cx + l[2] * cy), f.y + cy - (l[1] * cx + l[3] * cy)]; }
  function rebox(f, b) {
    const w1 = Math.max(0.01, b.x1 - b.x0), h1 = Math.max(0.01, b.y1 - b.y0), l = linOf(f);
    const vx = b.x0 + w1 / 2 - f.w / 2, vy = b.y0 + h1 / 2 - f.h / 2;
    return {x: f.x + f.w / 2 - w1 / 2 + l[0] * vx + l[2] * vy, y: f.y + f.h / 2 - h1 / 2 + l[1] * vx + l[3] * vy, w: w1, h: h1};
  }
  const STYLE = ['fills', 'strokes', 'strokeWeight', 'strokeAlign', 'strokeCap', 'strokeJoin', 'dash', 'fillStyle'];
  function styleOf(ids) {
    const out = {};
    for (const id of ids) { const n = S().get(id); if (!n || n.type === 'TEXT') continue; const has = (Array.isArray(n.fills) && n.fills.length) || (Array.isArray(n.strokes) && n.strokes.length) || n.fillStyle;
      if (has) { for (const k of STYLE) if (n[k] !== undefined) out[k] = JSON.parse(JSON.stringify(n[k])); return out; } }
    out.fills = [U().solid('#D9D9D9')];
    return out;
  }

  /* ================================================================== shape -> vector, boolean groups, flatten, masks */
  const SHAPES = {RECT: 1, ELLIPSE: 1, POLYGON: 1, STAR: 1, LINE: 1};
  const OP_NAME = {union: 'Union', subtract: 'Subtract', intersect: 'Intersect', exclude: 'Exclude'};
  function toVector(id, label) {
    const n = S().get(id);
    if (!n) return false;
    if (n.type === 'VECTOR') return true;
    if (!SHAPES[n.type] || !guard()) return false;
    const w = num(n.w, 100), h = n.type === 'LINE' ? 0 : num(n.h, 100), o = GEO().outlineSegs(n, n.type, w, h);
    const p = {type: 'VECTOR', path: GEO().segsToD(o.segs), radius: null, sides: null, ratio: null};
    if (n.type === 'LINE') p.h = 0.01;
    S().tx(label || 'Edit shape', () => S().set(id, p));
    panel();
    return S().get(id).type === 'VECTOR';
  }
  function editShape() {
    if (!guard()) return false;
    const ids = U().selIds();
    if (ids.length !== 1) { toast('Select one shape to edit its points.'); return false; }
    const n = S().get(ids[0]);
    if (isBool(n)) { toast('This is a ' + OP_NAME[n.bool].toLowerCase() + ' of several shapes. Flatten it first to edit its points.'); return false; }
    if (n.type !== 'VECTOR' && !SHAPES[n.type]) { toast('Only shapes have points to edit.'); return false; }
    if (!toVector(ids[0])) return false;
    return enter(ids[0]);
  }
  function bool(op) {
    if (!OP_NAME[op] || !guard()) return null;
    const ids = U().topLevel(U().selIds());
    if (ids.length === 1 && typeOf(ids[0]) === 'GROUP') {          /* a group: its children are combined; a boolean: another way of combining */
      S().tx(OP_NAME[op], () => { const n = S().get(ids[0]), p = {bool: op}; if (!isBool(n)) { Object.assign(p, styleOf(S().children(ids[0]))); if (/^Group( \d+)?$/.test(n.name || '')) p.name = OP_NAME[op]; } else if (OP_NAME[n.bool] === n.name) p.name = OP_NAME[op]; S().set(ids[0], p); });
      panel(); return ids[0];
    }
    if (ids.length < 2) { toast('Select two or more shapes to combine them.'); return null; }
    if (!ids.some(id => { const t = typeOf(id); return t !== 'TEXT' && t !== 'LINE'; })) { toast('Text and lines have no area to combine.'); return null; }
    const style = styleOf(ids);
    let gid = null;
    S().tx(OP_NAME[op], () => { gid = TL().act.group(); if (gid) S().set(gid, Object.assign({name: OP_NAME[op], bool: op}, style)); });
    if (gid) { HD.sel.set([gid]); if (ids.some(id => typeOf(id) === 'TEXT' || typeOf(id) === 'LINE')) toast('Text and lines take no part in the result.'); }
    panel();
    return gid;
  }
  /* a new VECTOR that shows path data d, written in the space of frame f (null = straight in the parent's space) */
  function vectorFrom(d, f, parent, before, props) {
    const segs = GEO().parsePath(d), b = GEO().pathBBox(d);
    if (!segs.length || !(b.x1 - b.x0 > 0.001 || b.y1 - b.y0 > 0.001)) return null;
    const fr = f || {x: 0, y: 0, w: 0, h: 0, rot: 0, fh: false, fv: false}, nb = rebox(fr, b);
    const p = Object.assign({}, props, {x: r2(nb.x), y: r2(nb.y), w: r2(nb.w), h: r2(nb.h), path: GEO().segsToD(shiftSegs(segs, -b.x0, -b.y0))});
    if (fr.rot) p.rot = fr.rot;
    if (fr.fh) p.flipH = true;
    if (fr.fv) p.flipV = true;
    return S().create('VECTOR', parent, p, before || undefined);
  }
  function nextSibling(id) { const sib = S().children(S().parent(id)), i = sib.indexOf(id); return i >= 0 && i + 1 < sib.length ? sib[i + 1] : null; }
  const KEEP = ['opacity', 'blend', 'effects', 'effectStyle', 'cons', 'sizeH', 'sizeV', 'layoutPos', 'mask', 'locked', 'reactions', 'exports'];
  function flatten() {
    if (!guard()) return null;
    const ids = U().topLevel(U().selIds());
    if (!ids.length) { toast('Select a boolean group or shapes to flatten.'); return null; }
    const n0 = S().get(ids[0]);
    if (ids.length === 1 && n0.type === 'VECTOR') { toast('This is already one vector.'); return ids[0]; }
    if (ids.length === 1 && SHAPES[n0.type]) { toVector(ids[0], 'Flatten'); return ids[0]; }
    const bad = ids.filter(id => { const t = typeOf(id); return !(t === 'VECTOR' || t === 'GROUP' || (SHAPES[t] && t !== 'LINE')); });
    if (bad.length) { toast('Flatten works on shapes, vectors and groups of them. ' + (typeOf(bad[0]) === 'TEXT' ? 'Text' : typeOf(bad[0]) === 'LINE' ? 'A line' : 'A ' + typeOf(bad[0]).toLowerCase()) + ' can not be flattened yet.'); return null; }
    let out = null, note = '';
    const parent = S().parent(ids[ids.length - 1]), before = nextSibling(ids[ids.length - 1]);
    S().tx('Flatten', () => {
      if (ids.length === 1 && isBool(n0)) {
        const g = GEO().boolPath(ids[0]);
        if (!g || !g.d) { note = 'Nothing is left of this ' + OP_NAME[n0.bool].toLowerCase() + ': there is no shape to keep.'; return; }
        const props = {name: n0.name || 'Vector'};
        for (const k of STYLE.concat(KEEP)) if (n0[k] !== undefined) props[k] = JSON.parse(JSON.stringify(n0[k]));
        out = vectorFrom(g.d, frameOf(n0), S().parent(ids[0]), nextSibling(ids[0]), props);
        if (out) S().remove([ids[0]]);
        return;
      }
      const d = GEO().combine('union', ids, parent);
      if (!d) { note = 'These layers have no outline to flatten.'; return; }
      const props = Object.assign({name: ids.length === 1 ? (n0.name || 'Vector') : U().nextName('VECTOR')}, styleOf(ids.length === 1 && n0.type === 'GROUP' ? S().children(ids[0]) : ids));
      out = vectorFrom(d, null, parent, before, props);
      if (out) S().remove(ids);
    });
    if (note) toast(note);
    if (out) { HD.sel.set([out]); panel(); }
    return out;
  }
  function mask() {
    if (!guard()) return;
    const ids = U().topLevel(U().selIds());
    if (!ids.length) { toast('Select the layer that should be the mask.'); return; }
    if (ids.length === 1) {
      const n = S().get(ids[0]), kids = S().children(ids[0]);
      const inner = n.type === 'GROUP' && !isBool(n) && kids.length && P(kids[0], 'mask') === true ? kids[0] : null;
      if (inner) { S().tx('Remove mask', () => S().set(inner, {mask: null})); panel(); return; }
      const on = n.mask === true;
      S().tx(on ? 'Remove mask' : 'Use as mask', () => S().set(ids[0], {mask: on ? null : true}));
      if (!on && nextSibling(ids[0]) === null) toast('A mask shows the layers ABOVE it in the same frame or group. Nothing is above this one yet.');
      panel(); return;
    }
    let gid = null;
    S().tx('Use as mask', () => { gid = TL().act.group(); if (gid) { S().set(gid, {name: 'Mask group'}); const kids = S().children(gid); if (kids.length) S().set(kids[0], {mask: true}); } });
    if (gid) HD.sel.set([gid]);
    panel();
  }

  /* ================================================================== vector edit mode
     E.subs is kept in a FROZEN frame (the node's own space when the mode was entered), so a point that is not touched
     never moves: after every step the path is written back with a box that hugs it (rebox) and the node stays where
     it is on the canvas. */
  let E = null;
  function mw() { return MX().mul(U().wm(S().parent(E.id)), frameMat(E.f)); }
  function toScr(m, x, y) { const w = MX().apply(m, x, y); return w2s(w[0], w[1]); }
  function toFrame(e) { return MX().apply(MX().inv(mw()), e.x, e.y); }
  function enter(id) {
    const n = S().get(id);
    if (!n || n.type !== 'VECTOR' || !canEdit() || P(id, 'locked') === true) return false;
    const subs = toModel(GEO().vectorSegs(n));
    if (!subs.length) { toast('This vector has no points.'); return false; }
    E = {id: id, f: frameOf(n), subs: subs, sel: new Set(), drag: null, hover: null, mine: false, marq: null};
    if (!(HD.sel.ids.length === 1 && HD.sel.ids[0] === id)) HD.sel.set([id]);
    if (TL().current !== 'vedit') TL().set('vedit');
    if (!E) return false;
    bar(true); redraw();
    return true;
  }
  function leave() { if (TL().current === 'vedit') TL().set('move'); else { E = null; bar(false); } }
  function resync() {
    const n = E && S().get(E.id);
    if (!n || n.type !== 'VECTOR') { leave(); return; }
    const old = E.sel;
    E.f = frameOf(n); E.subs = toModel(GEO().vectorSegs(n)); E.sel = new Set(); E.drag = null;
    for (const k of old) { const q = k.split('/'), s = E.subs[+q[0]]; if (s && s.pts[+q[1]]) E.sel.add(k); }
    bar(true); redraw();
  }
  /* write the model back: ONE store change; g = the gesture of a drag (so the whole drag is one undo step) */
  function commit(label, g) {
    if (!E) return;
    const live = E.subs.filter(s => s.pts.length > 0);
    if (!live.length) { const id = E.id; E.mine = true; try { HD.sel.clear(); S().tx('Delete', () => S().remove([id])); } finally { if (E) E.mine = false; } leave(); return; }
    const b = GEO().pathBBox(toD(live, 0, 0)), nb = rebox(E.f, b), d = toD(live, -b.x0, -b.y0);
    const vals = {path: d, x: r2(nb.x), y: r2(nb.y), w: r2(nb.w), h: r2(nb.h)};
    const fn = () => { S().set(E.id, vals); };
    E.mine = true;
    try { if (g) g.apply(fn); else S().tx(label || 'Edit shape', fn); } finally { E.mine = false; }
    const n = S().get(E.id);
    if (n) {
      /* an auto layout parent may have put the layer somewhere else: the frozen frame follows it */
      const dx = num(n.x, 0) - vals.x, dy = num(n.y, 0) - vals.y;
      if (Math.abs(dx) > 0.004 || Math.abs(dy) > 0.004) { E.f.x += dx; E.f.y += dy; }
    }
    redraw();
  }
  function ptAt(k) { const q = k.split('/'), s = E.subs[+q[0]]; return s ? s.pts[+q[1]] : null; }
  function segCount(s) { return s.pts.length < 2 ? 0 : s.closed ? s.pts.length : s.pts.length - 1; }
  function segPt(a, b, t) {
    if (!a.o && !b.i) return [a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t];
    const c1 = a.o || [a.x, a.y], c2 = b.i || [b.x, b.y], u = 1 - t, k0 = u * u * u, k1 = 3 * u * u * t, k2 = 3 * u * t * t, k3 = t * t * t;
    return [k0 * a.x + k1 * c1[0] + k2 * c2[0] + k3 * b.x, k0 * a.y + k1 * c1[1] + k2 * c2[1] + k3 * b.y];
  }
  /* what is under the pointer (screen px): a curve handle of a chosen point, a point, a segment */
  function hitAt(sx, sy) {
    const m = mw();
    for (const k of E.sel) {
      const p = ptAt(k);
      if (!p) continue;
      for (const which of ['i', 'o']) if (p[which]) { const q = toScr(m, p[which][0], p[which][1]); if (Math.hypot(q[0] - sx, q[1] - sy) <= 7) return {kind: 'handle', key: k, which: which}; }
    }
    let best = null, bd = 8;
    E.subs.forEach((s, si) => s.pts.forEach((p, pi) => { const q = toScr(m, p.x, p.y), d = Math.hypot(q[0] - sx, q[1] - sy); if (d <= bd) { bd = d; best = {kind: 'pt', key: si + '/' + pi}; } }));
    if (best) return best;
    bd = 6;
    E.subs.forEach((s, si) => {
      const n = s.pts.length;
      for (let j = 0; j < segCount(s); j++) {
        const a = s.pts[j], b = s.pts[(j + 1) % n];
        const dist = (t) => { const q = segPt(a, b, t), z = toScr(m, q[0], q[1]); return Math.hypot(z[0] - sx, z[1] - sy); };
        let bt = 0, bv = Infinity;
        for (let i = 0; i <= 32; i++) { const v = dist(i / 32); if (v < bv) { bv = v; bt = i / 32; } }
        let lo = Math.max(0, bt - 1 / 32), hi = Math.min(1, bt + 1 / 32);
        for (let i = 0; i < 18; i++) { const t1 = lo + (hi - lo) / 3, t2 = hi - (hi - lo) / 3; if (dist(t1) < dist(t2)) hi = t2; else lo = t1; }
        bt = (lo + hi) / 2; bv = dist(bt);
        if (bv <= bd) { bd = bv; best = {kind: 'seg', si: si, j: j, t: Math.max(0.02, Math.min(0.98, bt))}; }
      }
    });
    return best;
  }
  function insertPoint(si, j, t) {
    const s = E.subs[si], n = s.pts.length, a = s.pts[j], b = s.pts[(j + 1) % n];
    let q;
    if (!a.o && !b.i) q = {x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, i: null, o: null, sm: false};
    else {
      const p0 = [a.x, a.y], p1 = a.o || p0, p3 = [b.x, b.y], p2 = b.i || p3, L = (u, v) => [u[0] + (v[0] - u[0]) * t, u[1] + (v[1] - u[1]) * t];
      const q0 = L(p0, p1), q1 = L(p1, p2), q2 = L(p2, p3), r0 = L(q0, q1), r1 = L(q1, q2), x = L(r0, r1);
      a.o = q0; b.i = q2;
      q = {x: x[0], y: x[1], i: r0, o: r1, sm: true};
    }
    s.pts.splice(j + 1, 0, q);
    a.sm = isSmooth(a); b.sm = isSmooth(b);
    return si + '/' + (j + 1);
  }
  function deletePoints() {
    if (!E || !E.sel.size) return false;
    E.subs = E.subs.map((s, si) => ({closed: s.closed, pts: s.pts.filter((p, pi) => !E.sel.has(si + '/' + pi))})).filter(s => s.pts.length >= 2);
    E.sel = new Set();
    commit('Delete point'); bar(true);
    return true;
  }
  /* corner <-> smooth for the chosen points (keys = which; default the selection) */
  function toggleSmooth(keys) {
    const list = Array.from(keys || E.sel);
    if (!list.length) return;
    const anyCurve = list.some(k => { const p = ptAt(k); return p && (p.i || p.o); });
    for (const k of list) {
      const q = k.split('/'), s = E.subs[+q[0]], pi = +q[1], p = s && s.pts[pi];
      if (!p) continue;
      if (anyCurve) { p.i = null; p.o = null; p.sm = false; continue; }
      const n = s.pts.length, prev = s.closed || pi > 0 ? s.pts[(pi - 1 + n) % n] : null, next = s.closed || pi < n - 1 ? s.pts[(pi + 1) % n] : null;
      const a = prev || p, b = next || p, dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy);
      if (len < 1e-6) continue;
      const ux = dx / len, uy = dy / len;
      if (prev) { const l = Math.hypot(p.x - prev.x, p.y - prev.y) / 3; p.i = [p.x - ux * l, p.y - uy * l]; }
      if (next) { const l = Math.hypot(next.x - p.x, next.y - p.y) / 3; p.o = [p.x + ux * l, p.y + uy * l]; }
      p.sm = !!(p.i && p.o);
    }
    commit(anyCurve ? 'Corner point' : 'Smooth point'); bar(true);
  }
  function subsOfSel() { const out = new Set(); for (const k of E.sel) out.add(+k.split('/')[0]); if (!out.size) E.subs.forEach((s, i) => out.add(i)); return Array.from(out); }
  function toggleClosed() {
    const list = subsOfSel().map(i => E.subs[i]).filter(s => s && s.pts.length > 1);
    if (!list.length) return;
    const close = list.some(s => !s.closed);
    for (const s of list) s.closed = close;
    commit(close ? 'Close path' : 'Open path'); bar(true);
  }
  function moveSel(orig, dx, dy) {
    E.subs = cloneSubs(orig);
    for (const k of E.sel) { const p = ptAt(k); if (!p) continue; p.x += dx; p.y += dy; if (p.i) { p.i[0] += dx; p.i[1] += dy; } if (p.o) { p.o[0] += dx; p.o[1] += dy; } }
  }
  function selectAllPoints() { E.sel = new Set(); E.subs.forEach((s, si) => s.pts.forEach((p, pi) => E.sel.add(si + '/' + pi))); bar(true); redraw(); }

  const veditTool = {
    cursor: 'default',
    enter() { /* E is set by enter(id) before the tool is switched on */ },
    leave() { if (E && E.drag && E.drag.g) E.drag.g.end(); E = null; bar(false); redraw(); },
    down(e) {
      if (!E) return;
      const h = hitAt(e.sx, e.sy), f = toFrame(e), G = U().Gesture;
      if (h && h.kind === 'handle') { E.drag = {mode: 'handle', key: h.key, which: h.which, g: new G('Move handle')}; return; }
      if (h && h.kind === 'pt') {
        if (e.shift) { if (E.sel.has(h.key)) E.sel.delete(h.key); else E.sel.add(h.key); bar(true); if (!E.sel.has(h.key)) return; }
        else if (!E.sel.has(h.key)) { E.sel = new Set([h.key]); bar(true); }
        E.drag = {mode: 'pts', f0: f, sx: e.sx, sy: e.sy, orig: cloneSubs(E.subs), g: new G('Move point'), moved: false};
        return;
      }
      if (h && h.kind === 'seg') { E.drag = {mode: 'seg', si: h.si, j: h.j, t: h.t, f0: f, sx: e.sx, sy: e.sy, orig: cloneSubs(E.subs), g: new G('Bend curve'), moved: false}; return; }
      if (!e.shift) { E.sel = new Set(); bar(true); }
      E.drag = {mode: 'marq', sx: e.sx, sy: e.sy, base: new Set(E.sel)};
    },
    move(e) {
      if (!E) return;
      const d = E.drag;
      if (!d) {
        const h = hitAt(e.sx, e.sy), key = h ? h.kind + (h.key || (h.si + ':' + h.j)) + (h.which || '') : '';
        if (key !== (E.hoverKey || '')) { E.hoverKey = key; E.hover = h; redraw(); }
        if (TL().canvas) TL().canvas.style.cursor = h ? (h.kind === 'seg' ? 'copy' : 'move') : 'default';
        return;
      }
      const f = toFrame(e);
      if (d.mode === 'pts') {
        if (!d.moved && Math.hypot(e.sx - d.sx, e.sy - d.sy) < 3) return;
        d.moved = true;
        let dx = f[0] - d.f0[0], dy = f[1] - d.f0[1];
        if (e.shift) { if (Math.abs(dx) > Math.abs(dy)) dy = 0; else dx = 0; }
        moveSel(d.orig, dx, dy); commit('Move point', d.g);
      } else if (d.mode === 'handle') {
        const p = ptAt(d.key);
        if (!p) return;
        p[d.which] = [f[0], f[1]];
        const other = d.which === 'i' ? 'o' : 'i';
        if (e.alt) p.sm = false;
        else if (p.sm && p[other]) { const l = Math.hypot(p[other][0] - p.x, p[other][1] - p.y), vx = p.x - f[0], vy = p.y - f[1], vl = Math.hypot(vx, vy); if (vl > 1e-6) p[other] = [p.x + vx / vl * l, p.y + vy / vl * l]; }
        commit('Move handle', d.g);
      } else if (d.mode === 'seg') {
        if (!d.moved && Math.hypot(e.sx - d.sx, e.sy - d.sy) < 3) return;
        d.moved = true;
        E.subs = cloneSubs(d.orig);
        const s = E.subs[d.si], a = s.pts[d.j], b = s.pts[(d.j + 1) % s.pts.length], t = d.t;
        const p1 = a.o || [a.x + (b.x - a.x) / 3, a.y + (b.y - a.y) / 3], p2 = b.i || [b.x + (a.x - b.x) / 3, b.y + (a.y - b.y) / 3];
        const dx = f[0] - d.f0[0], dy = f[1] - d.f0[1];
        /* pull the two handles so that the point that was grabbed follows the pointer exactly */
        const wt = t <= 1 / 6 ? 0 : t <= 0.5 ? Math.pow((6 * t - 1) / 2, 3) / 2 : t <= 5 / 6 ? (1 - Math.pow((6 * (1 - t) - 1) / 2, 3)) / 2 + 0.5 : 1;
        const k1 = (1 - wt) / (3 * t * (1 - t) * (1 - t)), k2 = wt / (3 * t * t * (1 - t));
        a.o = [p1[0] + dx * k1, p1[1] + dy * k1]; b.i = [p2[0] + dx * k2, p2[1] + dy * k2];
        a.sm = isSmooth(a); b.sm = isSmooth(b);
        commit('Bend curve', d.g);
      } else if (d.mode === 'marq') {
        const x0 = Math.min(d.sx, e.sx), y0 = Math.min(d.sy, e.sy), x1 = Math.max(d.sx, e.sx), y1 = Math.max(d.sy, e.sy), m = mw();
        E.marq = [x0, y0, x1, y1];
        const sel = new Set(d.base);
        E.subs.forEach((s, si) => s.pts.forEach((p, pi) => { const q = toScr(m, p.x, p.y); if (q[0] >= x0 && q[0] <= x1 && q[1] >= y0 && q[1] <= y1) sel.add(si + '/' + pi); }));
        E.sel = sel; redraw();
      }
    },
    up(e) {
      if (!E) return;
      const d = E.drag;
      E.drag = null; E.marq = null;
      if (!d) return;
      if (d.g) d.g.end();
      if (d.mode === 'seg' && !d.moved) { E.sel = new Set([insertPoint(d.si, d.j, d.t)]); commit('Add point'); }
      if (d.mode === 'pts' && !d.moved && !e.shift && E.sel.size > 1) { const h = hitAt(e.sx, e.sy); if (h && h.kind === 'pt') E.sel = new Set([h.key]); }
      bar(true); redraw();
    },
    dbl(e) {
      if (!E) return;
      const h = hitAt(e.sx, e.sy);
      if (h && h.kind === 'pt') { E.sel = new Set([h.key]); toggleSmooth([h.key]); return; }
      if (!h) leave();
    },
    key(ev) {
      if (!E) return false;
      if (ev.key === 'Escape') { if (E.drag) return true; if (E.sel.size) { E.sel = new Set(); bar(true); redraw(); } else leave(); return true; }
      if (ev.key === 'Enter') { leave(); return true; }
      if (/^Arrow/.test(ev.key) && E.sel.size && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        const k = (ev.shiftKey ? 10 : 1), wx = ev.key === 'ArrowLeft' ? -k : ev.key === 'ArrowRight' ? k : 0, wy = ev.key === 'ArrowUp' ? -k : ev.key === 'ArrowDown' ? k : 0;
        const im = MX().inv(mw()), dx = im[0] * wx + im[2] * wy, dy = im[1] * wx + im[3] * wy;
        moveSel(E.subs, dx, dy); commit('Nudge point');
        return true;
      }
      return false;
    }
  };

  /* the small bar over the canvas while points are edited */
  let barEl = null, barBtns = null;
  function bar(on) {
    const host = TL().host, h = HD.ui && HD.ui.h;
    if (!on || !E || !host || !h) { if (barEl && barEl.parentNode) barEl.parentNode.removeChild(barEl); barEl = null; return; }
    if (!barEl || barEl.parentNode !== host) {
      if (barEl && barEl.parentNode) barEl.parentNode.removeChild(barEl);
      const btn = (text, title, run) => h('button', {class: 'hd-btn', type: 'button', text: text, title: title, on: {click: () => { run(); if (TL().canvas) TL().canvas.focus({preventScroll: true}); }}});
      barBtns = {smooth: btn('Smooth', 'Make the chosen points smooth or sharp (double-click a point)', () => toggleSmooth()),
        close: btn('Close path', 'Join the last point to the first, or open the path again', toggleClosed),
        del: btn('Delete point', 'Remove the chosen points (Delete)', deletePoints),
        done: h('button', {class: 'hd-btn pri', type: 'button', text: 'Done', title: 'Leave edit mode (Enter)', on: {click: leave}})};
      barEl = h('div', {class: 'hdv-bar', role: 'toolbar', 'aria-label': 'Edit shape'}, h('span', {class: 'hdv-title', text: 'Editing shape'}),
        h('span', {class: 'hdv-hint', text: 'Drag a point or a curve. Click a line to add a point.'}), barBtns.smooth, barBtns.close, barBtns.del, h('span', {class: 'hdv-sep'}), barBtns.done);
      host.appendChild(barEl);
    }
    barEl.classList.toggle('below', rulersOn);
    const pts = Array.from(E.sel).map(ptAt).filter(Boolean), curved = pts.some(p => p.i || p.o), subs = subsOfSel().map(i => E.subs[i]).filter(Boolean);
    barBtns.smooth.textContent = curved ? 'Corner' : 'Smooth'; barBtns.smooth.disabled = !pts.length;
    barBtns.del.disabled = !pts.length;
    barBtns.close.textContent = subs.length && subs.every(s => s.closed) ? 'Open path' : 'Close path';
  }
  function drawEdit(ctx) {
    if (!E || !S().has(E.id)) return;
    const m = mw(), Sx = (p) => toScr(m, p[0], p[1]);
    ctx.save();
    ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    /* the path */
    ctx.beginPath();
    for (const s of E.subs) {
      const n = s.pts.length;
      if (!n) continue;
      const f = Sx([s.pts[0].x, s.pts[0].y]);
      ctx.moveTo(f[0], f[1]);
      for (let j = 0; j < segCount(s); j++) {
        const a = s.pts[j], b = s.pts[(j + 1) % n], q = Sx([b.x, b.y]);
        if (a.o || b.i) { const c1 = Sx(a.o || [a.x, a.y]), c2 = Sx(b.i || [b.x, b.y]); ctx.bezierCurveTo(c1[0], c1[1], c2[0], c2[1], q[0], q[1]); } else ctx.lineTo(q[0], q[1]);
      }
    }
    ctx.strokeStyle = '#FFFFFF'; ctx.lineWidth = 3; ctx.globalAlpha = 0.7; ctx.stroke();
    ctx.globalAlpha = 1; ctx.strokeStyle = ACC; ctx.lineWidth = 1.5; ctx.stroke();
    /* the segment under the pointer: where a click adds a point */
    const hv = E.hover;
    if (hv && hv.kind === 'seg' && !E.drag && E.subs[hv.si]) { const s = E.subs[hv.si], a = s.pts[hv.j], b = s.pts[(hv.j + 1) % s.pts.length]; if (a && b) { const q = segPt(a, b, hv.t), z = Sx(q); ctx.beginPath(); ctx.arc(z[0], z[1], 4, 0, TAU); ctx.fillStyle = '#FFFFFF'; ctx.fill(); ctx.strokeStyle = ACC; ctx.lineWidth = 1.5; ctx.stroke(); } }
    /* handles of the chosen points */
    for (const k of E.sel) {
      const p = ptAt(k);
      if (!p) continue;
      const c = Sx([p.x, p.y]);
      for (const which of ['i', 'o']) if (p[which]) {
        const q = Sx(p[which]);
        ctx.beginPath(); ctx.moveTo(c[0], c[1]); ctx.lineTo(q[0], q[1]); ctx.strokeStyle = ACC; ctx.lineWidth = 1; ctx.stroke();
        ctx.beginPath(); ctx.arc(q[0], q[1], 3.5, 0, TAU); ctx.fillStyle = '#FFFFFF'; ctx.fill(); ctx.strokeStyle = ACC; ctx.lineWidth = 1.5; ctx.stroke();
      }
    }
    /* the points: a square = a corner, a circle = a curve point; filled = chosen */
    E.subs.forEach((s, si) => s.pts.forEach((p, pi) => {
      const c = Sx([p.x, p.y]), on = E.sel.has(si + '/' + pi), hot = hv && hv.kind === 'pt' && hv.key === si + '/' + pi, r = on || hot ? 4.5 : 3.5;
      ctx.beginPath();
      if (p.i || p.o) ctx.arc(c[0], c[1], r, 0, TAU); else ctx.rect(c[0] - r, c[1] - r, r * 2, r * 2);
      ctx.fillStyle = on ? ACC : '#FFFFFF'; ctx.fill();
      ctx.strokeStyle = on ? '#FFFFFF' : ACC; ctx.lineWidth = 1.5; ctx.stroke();
    }));
    if (E.marq) { const q = E.marq; ctx.fillStyle = 'rgba(110,85,240,.10)'; ctx.strokeStyle = ACC; ctx.lineWidth = 1; ctx.fillRect(q[0], q[1], q[2] - q[0], q[3] - q[1]); ctx.strokeRect(Math.round(q[0]) + 0.5, Math.round(q[1]) + 0.5, Math.round(q[2] - q[0]), Math.round(q[3] - q[1])); }
    ctx.restore();
  }

  /* ================================================================== rulers + guides
     Rulers are drawn on the canvas overlay (top and left, 20 px). A guide is pulled out of a ruler and kept on the
     PAGE node: guides = [{axis: 'x' | 'y', pos}] (axis x = an upright line at world x = pos). Moving layers snap to
     them (HD.tools.snapExtra). Rulers off = guides hidden and not snapped to. */
  const RS = 20;
  let rulersOn = pref('rulers', false), gridsOn = pref('grids', true);
  let hoverGuide = -1, dragGuide = null, colors = null;
  function guidesOf(page) { const n = S().get(page || HD.sel.page); return n && Array.isArray(n.guides) ? n.guides.filter(g => g && (g.axis === 'x' || g.axis === 'y') && typeof g.pos === 'number' && isFinite(g.pos)) : []; }
  function setGuides(list, g, label) {
    const page = HD.sel.page;
    if (!page || !S().has(page)) return;
    const fn = () => S().set(page, {guides: list.length ? list : null});
    if (g) g.apply(fn); else S().tx(label || 'Guides', fn);
  }
  function setRulers(on) { rulersOn = !!on; setPref('rulers', rulersOn); hoverGuide = -1; if (E) bar(true); redraw(); }
  function setGrids(on) { gridsOn = !!on; setPref('grids', gridsOn); R().showGrids = gridsOn; redraw(); }
  function themeColors() {
    if (colors) return colors;
    let cs = null;
    try { cs = getComputedStyle(document.documentElement); } catch (e) { cs = null; }
    const v = (name, d) => { const x = cs ? String(cs.getPropertyValue(name) || '').trim() : ''; return x || d; };
    colors = {bg: v('--side-bg', '#F8F8F7'), line: v('--hair2', '#DCDCD8'), tick: v('--dim', '#8B8B92'), text: v('--mut', '#5C5C63'), ink: v('--ink', '#1A1A1F')};
    return colors;
  }
  function rulerStep(z) { const want = 64 / z, p = Math.pow(10, Math.floor(Math.log10(want))); for (const k of [1, 2, 5, 10]) if (k * p >= want) return k * p; return 10 * p; }
  function drawRulers(ctx) {
    const cv = TL().canvas;
    if (!cv) return;
    const W = cv.clientWidth, H = cv.clientHeight, v = R().view, z = v.zoom || 1, c = themeColors();
    const page = HD.sel.page, list = guidesOf(page), ids = U().selIds();
    /* guides, under the rulers */
    list.forEach((g, i) => {
      const hot = i === hoverGuide || (dragGuide && dragGuide.i === i);
      let snapped = false;
      if (!hot && ids.length && ids.length <= 40) for (const id of ids) { const b = U().aabb(id); const vals = g.axis === 'x' ? [b.x, b.x + b.w / 2, b.x + b.w] : [b.y, b.y + b.h / 2, b.y + b.h]; if (vals.some(t => Math.abs(t - g.pos) < 0.011)) { snapped = true; break; } }
      ctx.fillStyle = hot ? ACC : RED; ctx.globalAlpha = hot || snapped ? 1 : 0.75;
      const t = hot || snapped ? 1.5 : 1;
      if (g.axis === 'x') { const x = Math.round(g.pos * z + v.x); if (x >= RS && x <= W) ctx.fillRect(x - (t > 1 ? 0.75 : 0), RS, t, H - RS); }
      else { const y = Math.round(g.pos * z + v.y); if (y >= RS && y <= H) ctx.fillRect(RS, y - (t > 1 ? 0.75 : 0), W - RS, t); }
    });
    ctx.globalAlpha = 1;
    ctx.fillStyle = c.bg;
    ctx.fillRect(0, 0, W, RS); ctx.fillRect(0, 0, RS, H);
    /* where the selection lies */
    const u = ids.length ? U().union(ids) : null;
    if (u) { ctx.fillStyle = 'rgba(110,85,240,.22)'; const a = w2s(u.x, u.y), b = w2s(u.x + u.w, u.y + u.h); ctx.fillRect(Math.max(RS, a[0]), 0, Math.max(0, Math.min(W, b[0]) - Math.max(RS, a[0])), RS); ctx.fillRect(0, Math.max(RS, a[1]), RS, Math.max(0, Math.min(H, b[1]) - Math.max(RS, a[1]))); }
    const step = rulerStep(z), minor = step / (String(step / Math.pow(10, Math.floor(Math.log10(step)))).charAt(0) === '2' ? 4 : 5);
    ctx.fillStyle = c.tick; ctx.font = '11px "Schibsted Grotesk", system-ui, sans-serif'; ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
    const label = (val) => fmt(Math.abs(val) < 1e-9 ? 0 : val);
    for (let wx = Math.floor(-v.x / z / minor) * minor; wx * z + v.x < W; wx += minor) {
      const x = Math.round(wx * z + v.x);
      if (x < RS) continue;
      const major = Math.abs(wx / step - Math.round(wx / step)) < 1e-6;
      ctx.fillStyle = c.tick; ctx.fillRect(x, major ? RS - 9 : RS - 4, 1, major ? 9 : 4);
      if (major) { ctx.fillStyle = c.text; ctx.fillText(label(wx), x + 3, 11); }
    }
    for (let wy = Math.floor(-v.y / z / minor) * minor; wy * z + v.y < H; wy += minor) {
      const y = Math.round(wy * z + v.y);
      if (y < RS) continue;
      const major = Math.abs(wy / step - Math.round(wy / step)) < 1e-6;
      ctx.fillStyle = c.tick; ctx.fillRect(major ? RS - 9 : RS - 4, y, major ? 9 : 4, 1);
      if (major) { ctx.save(); ctx.translate(11, y + 3); ctx.rotate(-Math.PI / 2); ctx.textAlign = 'right'; ctx.fillStyle = c.text; ctx.fillText(label(wy), 0, 0); ctx.restore(); }
    }
    ctx.fillStyle = c.bg; ctx.fillRect(0, 0, RS, RS);
    ctx.fillStyle = c.line; ctx.fillRect(0, RS - 1, W, 1); ctx.fillRect(RS - 1, 0, 1, H);
    if (dragGuide && dragGuide.pos !== null) { const s = dragGuide.axis === 'x' ? [dragGuide.pos * z + v.x + 8, Math.max(RS + 6, dragGuide.sy - 26)] : [Math.max(RS + 30, dragGuide.sx + 14), dragGuide.pos * z + v.y + 6]; badge(ctx, fmt(dragGuide.pos), s[0] + 14, s[1], ACC); }
  }
  function badge(ctx, text, x, y, color) {
    ctx.font = '500 11px "Schibsted Grotesk", system-ui, sans-serif';
    const w = Math.ceil(ctx.measureText(text).width) + 12, x0 = Math.round(x - w / 2), y0 = Math.round(y);
    ctx.fillStyle = color; ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(x0, y0, w, 20, 5); else ctx.rect(x0, y0, w, 20);
    ctx.fill();
    ctx.fillStyle = '#FFFFFF'; ctx.textBaseline = 'middle'; ctx.textAlign = 'center'; ctx.fillText(text, x0 + w / 2, y0 + 10.5); ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
  }
  function guideAt(sx, sy) {
    if (!rulersOn || sx < RS || sy < RS) return -1;
    const v = R().view, z = v.zoom || 1, list = guidesOf();
    let best = -1, bd = 4;
    list.forEach((g, i) => { const d = g.axis === 'x' ? Math.abs(g.pos * z + v.x - sx) : Math.abs(g.pos * z + v.y - sy); if (d <= bd) { bd = d; best = i; } });
    if (best < 0) return -1;
    /* next to the selection its own handles win, so an edge that was snapped to a guide can still be resized */
    const ids = U().selIds();
    if (ids.length) { const u = U().union(ids); if (u) { const a = w2s(u.x, u.y), b = w2s(u.x + u.w, u.y + u.h); if (sx >= a[0] - 9 && sx <= b[0] + 9 && sy >= a[1] - 9 && sy <= b[1] + 9) return -1; } }
    return best;
  }
  HD.tools.snapExtra = function () {
    if (!rulersOn) return [];
    return guidesOf().map(g => (g.axis === 'x' ? {x: g.pos, y: NaN, w: 0, h: NaN, guide: true} : {x: NaN, y: g.pos, w: NaN, h: 0, guide: true}));
  };

  /* ================================================================== gradient handles on the canvas
     While the colour picker has a gradient open (HD.ui.state.paint), its start and end, and its colour stops, can be
     dragged on the layer itself. */
  function livePaint() {
    const lp = HD.ui && HD.ui.state && HD.ui.state.paint;
    if (!lp || lp.solidOnly) return null;
    let p = null;
    try { p = lp.get(); } catch (e) { p = null; }
    if (!p || (p.type !== 'linear' && p.type !== 'radial' && p.type !== 'angular')) return null;
    const ids = U().selIds();
    if (!ids.length) return null;
    const n = S().get(ids[0]);
    if (!n) return null;
    const lin = p.type === 'linear';
    const from = Array.isArray(p.from) ? p.from : (lin ? [0.5, 0] : [0.5, 0.5]), to = Array.isArray(p.to) ? p.to : (lin ? [0.5, 1] : [1, 0.5]);
    return {lp: lp, p: p, id: ids[0], w: num(n.w, 100), h: n.type === 'LINE' ? 0 : num(n.h, 100), from: [num(+from[0], 0.5), num(+from[1], 0)], to: [num(+to[0], 0.5), num(+to[1], 1)], m: U().wm(ids[0])};
  }
  function gradPts(g) {
    const A = (u) => { const w = MX().apply(g.m, u[0] * g.w, u[1] * g.h); return w2s(w[0], w[1]); };
    const a = A(g.from), b = A(g.to), stops = [];
    if (g.p.type !== 'angular' && Array.isArray(g.p.stops)) g.p.stops.forEach((s, i) => { const t = Math.max(0, Math.min(1, num(+s.pos, 0))); stops.push({i: i, x: a[0] + (b[0] - a[0]) * t, y: a[1] + (b[1] - a[1]) * t, color: s.color}); });
    return {a: a, b: b, stops: stops, A: A};
  }
  function gradHit(sx, sy) {
    const g = livePaint();
    if (!g || !canEdit()) return null;
    const q = gradPts(g);
    for (const s of q.stops) if (s.i > 0 && s.i < q.stops.length - 1 && Math.hypot(s.x - sx, s.y - sy) <= 7) return {kind: 'gstop', i: s.i};
    if (Math.hypot(q.b[0] - sx, q.b[1] - sy) <= 9) return {kind: 'gend', which: 'to'};
    if (Math.hypot(q.a[0] - sx, q.a[1] - sy) <= 9) return {kind: 'gend', which: 'from'};
    for (const s of q.stops) if (Math.hypot(s.x - sx, s.y - sy) <= 7) return {kind: 'gstop', i: s.i};
    return null;
  }
  function drawGradient(ctx) {
    const g = livePaint();
    if (!g) return;
    const q = gradPts(g), sel = g.lp.stop;
    ctx.save();
    if (g.p.type === 'radial') {
      /* the rim of the gradient: a circle in the 0..1 space of the box = an ellipse on the layer */
      const r = Math.hypot(g.to[0] - g.from[0], g.to[1] - g.from[1]);
      ctx.beginPath();
      for (let i = 0; i <= 64; i++) { const a = i / 64 * TAU, s = q.A([g.from[0] + Math.cos(a) * r, g.from[1] + Math.sin(a) * r]); if (i) ctx.lineTo(s[0], s[1]); else ctx.moveTo(s[0], s[1]); }
      ctx.strokeStyle = '#FFFFFF'; ctx.lineWidth = 2.5; ctx.stroke(); ctx.setLineDash([4, 3]); ctx.strokeStyle = ACC; ctx.lineWidth = 1; ctx.stroke(); ctx.setLineDash([]);
    }
    ctx.beginPath(); ctx.moveTo(q.a[0], q.a[1]); ctx.lineTo(q.b[0], q.b[1]);
    ctx.strokeStyle = '#FFFFFF'; ctx.lineWidth = 4; ctx.lineCap = 'round'; ctx.stroke(); ctx.strokeStyle = ACC; ctx.lineWidth = 1.5; ctx.stroke();
    for (const e of [q.a, q.b]) { ctx.beginPath(); ctx.arc(e[0], e[1], 6, 0, TAU); ctx.fillStyle = '#FFFFFF'; ctx.fill(); ctx.strokeStyle = ACC; ctx.lineWidth = 2; ctx.stroke(); }
    for (const s of q.stops) {
      const on = s.i === sel, r = on ? 6 : 4.5;
      ctx.beginPath(); ctx.arc(s.x, s.y, r + 1.5, 0, TAU); ctx.fillStyle = on ? ACC : '#FFFFFF'; ctx.fill();
      ctx.beginPath(); ctx.arc(s.x, s.y, r, 0, TAU); ctx.fillStyle = /^#[0-9a-fA-F]{3,8}$/.test(String(s.color)) ? s.color : '#000000'; ctx.fill();
      ctx.strokeStyle = 'rgba(0,0,0,.25)'; ctx.lineWidth = 1; ctx.stroke();
    }
    ctx.restore();
  }

  /* ================================================================== distances (hold Alt over another layer) */
  let altDown = false, ptr = null;
  function drawMeasure(ctx) {
    if (!altDown || !ptr || TL().current !== 'move' || (TL().state && TL().state.drag)) return;
    const ids = U().selIds();
    if (!ids.length) return;
    const deep = R().hitTest(ptr[0], ptr[1], {deep: true});
    if (!deep) return;
    /* what the distance is measured to: the layer under the pointer; over the selection itself, the frame around it */
    const selSet = new Set(ids), ch = U().chain(deep), si = ch.findIndex(c => selSet.has(c));
    let target = null;
    if (si >= 0) target = si > 0 ? ch[si - 1] : null;
    else { const k = ch.indexOf(S().parent(ids[0])); target = k >= 0 && k + 1 < ch.length ? ch[k + 1] : (R().hitTest(ptr[0], ptr[1]) || deep); }
    if (!target || selSet.has(target)) return;
    const a = U().union(ids), b = U().aabb(target);
    if (!a || !b) return;
    const X = (x, y) => w2s(x, y);
    ctx.save();
    ctx.strokeStyle = MEASURE; ctx.fillStyle = MEASURE; ctx.lineWidth = 1;
    const p0 = X(b.x, b.y), p1 = X(b.x + b.w, b.y + b.h);
    ctx.strokeRect(Math.round(p0[0]) + 0.5, Math.round(p0[1]) + 0.5, Math.round(p1[0] - p0[0]), Math.round(p1[1] - p0[1]));
    const line = (x0, y0, x1, y1, val, horiz) => {
      if (Math.abs(val) < 0.005) return;
      const s0 = X(x0, y0), s1 = X(x1, y1);
      ctx.beginPath(); ctx.moveTo(Math.round(s0[0]) + 0.5, Math.round(s0[1]) + 0.5); ctx.lineTo(Math.round(s1[0]) + 0.5, Math.round(s1[1]) + 0.5); ctx.stroke();
      badge(ctx, fmt(Math.abs(val)), (s0[0] + s1[0]) / 2 + (horiz ? 0 : 24), (s0[1] + s1[1]) / 2 + (horiz ? 5 : -10), MEASURE);
      ctx.strokeStyle = MEASURE; ctx.fillStyle = MEASURE;
    };
    /* a dashed line from the target's edge to where the distance is measured, when that is beside the target */
    const ext = (x0, y0, x1, y1) => { const s0 = X(x0, y0), s1 = X(x1, y1); ctx.save(); ctx.setLineDash([3, 3]); ctx.beginPath(); ctx.moveTo(s0[0], s0[1]); ctx.lineTo(s1[0], s1[1]); ctx.stroke(); ctx.restore(); };
    const ay = a.y + a.h / 2, ax = a.x + a.w / 2, ar = a.x + a.w, ab = a.y + a.h, br = b.x + b.w, bb = b.y + b.h;
    const hx = (edge) => { if (ay < b.y) ext(edge, ay, edge, b.y); else if (ay > bb) ext(edge, bb, edge, ay); };
    const vy = (edge) => { if (ax < b.x) ext(ax, edge, b.x, edge); else if (ax > br) ext(br, edge, ax, edge); };
    if (ar <= b.x) { line(ar, ay, b.x, ay, b.x - ar, true); hx(b.x); }
    else if (br <= a.x) { line(br, ay, a.x, ay, a.x - br, true); hx(br); }
    else { line(Math.min(a.x, b.x), ay, Math.max(a.x, b.x), ay, a.x - b.x, true); line(Math.min(ar, br), ay, Math.max(ar, br), ay, br - ar, true); }
    if (ab <= b.y) { line(ax, ab, ax, b.y, b.y - ab, false); vy(b.y); }
    else if (bb <= a.y) { line(ax, bb, ax, a.y, a.y - bb, false); vy(bb); }
    else { line(ax, Math.min(a.y, b.y), ax, Math.max(a.y, b.y), a.y - b.y, false); line(ax, Math.min(ab, bb), ax, Math.max(ab, bb), bb - ab, false); }
    ctx.restore();
  }

  /* ================================================================== pointer + keys
     Gradient handles, rulers and guides are grabbed BEFORE the tools see the press (a capture listener on the window:
     it also runs before the click-outside that would close the colour picker). */
  let wired = null, overlayOn = false;
  function localXY(ev) { const r = TL().canvas.getBoundingClientRect(); return [ev.clientX - r.left, ev.clientY - r.top]; }
  function typing(ev) { const t = ev.target; return !!(t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)); }
  function track(move, up) {
    const mv = (ev) => { ev.stopPropagation(); ev.preventDefault(); move(ev); };
    const end = (ev) => { window.removeEventListener('pointermove', mv, true); window.removeEventListener('pointerup', end, true); window.removeEventListener('pointercancel', end, true); ev.stopPropagation(); up(ev); };
    window.addEventListener('pointermove', mv, true); window.addEventListener('pointerup', end, true); window.addEventListener('pointercancel', end, true);
  }
  function onDown(ev) {
    const cv = TL().canvas;
    if (!cv || ev.target !== cv || ev.button !== 0 || TL().panOnly || (TL().state && TL().state.spaceDown)) return;
    const s = localXY(ev), G = U().Gesture;
    const gh = gradHit(s[0], s[1]);
    if (gh) {
      ev.stopPropagation(); ev.preventDefault();
      const g = new G('Gradient'), lp = HD.ui.state.paint;
      if (gh.kind === 'gstop') lp.stop = gh.i;
      track((e2) => {
        const live = livePaint();
        if (!live) return;
        const q = localXY(e2), w = R().screenToWorld(q[0], q[1]), l = MX().apply(MX().inv(live.m), w[0], w[1]);
        const p = JSON.parse(JSON.stringify(live.p));
        if (gh.kind === 'gend') {
          let ux = live.w > 0.001 ? l[0] / live.w : 0.5, uy = live.h > 0.001 ? l[1] / live.h : 0.5;
          const other = gh.which === 'from' ? live.to : live.from;
          if (e2.shiftKey) { if (Math.abs((ux - other[0]) * live.w) > Math.abs((uy - other[1]) * live.h)) uy = other[1]; else ux = other[0]; }
          p[gh.which] = [Math.round(ux * 1000) / 1000, Math.round(uy * 1000) / 1000];
          if (!Array.isArray(p[gh.which === 'from' ? 'to' : 'from'])) p[gh.which === 'from' ? 'to' : 'from'] = other.slice();
        } else {
          const pts = gradPts(live), vx = pts.b[0] - pts.a[0], vy = pts.b[1] - pts.a[1], ll = vx * vx + vy * vy;
          if (!ll || !p.stops[gh.i]) return;
          const lo = gh.i > 0 ? num(+p.stops[gh.i - 1].pos, 0) : 0, hi = gh.i < p.stops.length - 1 ? num(+p.stops[gh.i + 1].pos, 1) : 1;
          p.stops[gh.i].pos = Math.round(Math.max(lo, Math.min(hi, ((q[0] - pts.a[0]) * vx + (q[1] - pts.a[1]) * vy) / ll)) * 1000) / 1000;
        }
        lp.set(p, g); redraw();
      }, () => { g.end(); redraw(); });
      return;
    }
    if (!rulersOn) return;
    const inTop = s[1] < RS, inLeft = s[0] < RS;
    let gi = -1;
    if (!inTop && !inLeft && TL().current === 'move') gi = guideAt(s[0], s[1]);
    if (!inTop && !inLeft && gi < 0) return;
    ev.stopPropagation(); ev.preventDefault();
    try { cv.focus({preventScroll: true}); } catch (e) { /* not focusable */ }
    if (!canEdit() || (inTop && inLeft)) return;
    const list = guidesOf().map(g => ({axis: g.axis, pos: g.pos})), g = new G(gi >= 0 ? 'Move guide' : 'Add guide');
    const axis = gi >= 0 ? list[gi].axis : inTop ? 'y' : 'x';
    dragGuide = {i: gi, axis: axis, pos: gi >= 0 ? list[gi].pos : null, sx: s[0], sy: s[1]};
    track((e2) => {
      const q = localXY(e2), w = R().screenToWorld(q[0], q[1]), out = axis === 'x' ? q[0] < RS : q[1] < RS;
      dragGuide.sx = q[0]; dragGuide.sy = q[1];
      const step = zoom() >= 8 ? 0.5 : 1, pos = Math.round((axis === 'x' ? w[0] : w[1]) / step) * step;
      const next = list.slice();
      if (out) { if (dragGuide.i >= 0) next.splice(dragGuide.i, 1); dragGuide.pos = null; dragGuide.out = true; }
      else { dragGuide.out = false; dragGuide.pos = pos; if (dragGuide.i >= 0) next[dragGuide.i] = {axis: axis, pos: pos}; else { next.push({axis: axis, pos: pos}); } }
      if (!out && dragGuide.i < 0) { dragGuide.i = list.length; list.push({axis: axis, pos: pos}); }
      setGuides(next, g);
      cv.style.cursor = out ? 'not-allowed' : axis === 'x' ? 'col-resize' : 'row-resize';
      redraw();
    }, () => { g.end(); dragGuide = null; hoverGuide = -1; cv.style.cursor = 'default'; redraw(); });
  }
  function onHover(ev) {
    const cv = TL().canvas;
    if (!cv) return;
    const s = localXY(ev), w = R().screenToWorld(s[0], s[1]);
    ptr = w;
    if (altDown) redraw();
    if (dragGuide || (TL().state && (TL().state.drag || TL().state.down))) return;
    if (livePaint() && gradHit(s[0], s[1])) { cv.style.cursor = 'grab'; return; }
    if (!rulersOn) return;
    if (s[0] < RS || s[1] < RS) { if (hoverGuide !== -1) { hoverGuide = -1; redraw(); } cv.style.cursor = s[0] < RS && s[1] < RS ? 'default' : s[1] < RS ? 'row-resize' : 'col-resize'; return; }
    const gi = TL().current === 'move' && canEdit() ? guideAt(s[0], s[1]) : -1;
    if (gi !== hoverGuide) { hoverGuide = gi; redraw(); }
    if (gi >= 0) cv.style.cursor = guidesOf()[gi].axis === 'x' ? 'col-resize' : 'row-resize';
  }
  function onKeyCapture(ev) {
    if (ev.key === 'Alt') { if (!altDown && HD.ui && HD.ui.mounted && U().selIds().length && document.activeElement === TL().canvas) { altDown = true; ev.preventDefault(); redraw(); } return; }
    if (!E || TL().current !== 'vedit' || typing(ev) || (ev.target && ev.target.closest && ev.target.closest('.hd-pop, .hd-modal'))) return;
    const mod = ev.ctrlKey || ev.metaKey;
    if ((ev.key === 'Delete' || ev.key === 'Backspace') && !mod) { ev.preventDefault(); ev.stopImmediatePropagation(); deletePoints(); }
    else if (mod && !ev.shiftKey && !ev.altKey && (ev.key === 'a' || ev.key === 'A')) { ev.preventDefault(); ev.stopImmediatePropagation(); selectAllPoints(); }
  }
  function overlay(ctx) {
    const cv = TL().canvas;
    if (cv && cv !== wired) { wired = cv; cv.addEventListener('pointermove', onHover); cv.addEventListener('pointerleave', () => { ptr = null; if (hoverGuide !== -1) { hoverGuide = -1; redraw(); } }); }
    if (R().showGrids !== gridsOn) R().showGrids = gridsOn;
    if (E) drawEdit(ctx);
    drawGradient(ctx);
    drawMeasure(ctx);
    if (rulersOn) drawRulers(ctx);
  }

  /* ================================================================== Design panel: "Layout grid" and "Shape" */
  const FRAMEY = {FRAME: 1, COMPONENT: 1, SECTION: 1};
  const GRID_NEW = {grid: {type: 'grid', size: 10}, columns: {type: 'columns', count: 5, gutter: 20, margin: 0}, rows: {type: 'rows', count: 5, gutter: 20, margin: 0}};
  function ib(icon, title, run) { const b = HD.ui.h('button', {class: 'hd-ib sm', type: 'button', title: title, 'aria-label': title}, HD.ui.icon(icon)); b.addEventListener('click', run); return b; }
  function gridSection(el, ids) {
    const ui = HD.ui, h = ui.h;
    if (!ids.length || !ids.every(id => FRAMEY[typeOf(id)])) return;
    const edit = canEdit(), first = JSON.stringify(P(ids[0], 'grids') || []), mixed = ids.some(id => JSON.stringify(P(id, 'grids') || []) !== first);
    const list = () => { const v = P(ids[0], 'grids'); return Array.isArray(v) ? v : []; };
    const setList = (arr, g) => { if (!canEdit()) return; const fn = () => { for (const id of ids) if (S().has(id)) S().set(id, {grids: arr.length ? arr : null}); }; if (g) g.apply(fn); else S().tx('Layout grid', fn); redraw(); };
    const fresh = (type, old) => Object.assign({}, GRID_NEW[type], {color: (old && old.color) || '#FF0000', opacity: old && old.opacity !== undefined ? old.opacity : 0.1, visible: !old || old.visible !== false});
    const addGrid = () => { const a = mixed ? [] : list().slice(); a.push(fresh(a.some(x => x && x.type !== 'columns') || !a.length ? (a.length ? 'columns' : 'grid') : 'rows')); setList(a); if (!gridsOn) setGrids(true); panel(); };
    const s = ui.section(el, 'Layout grid', [edit ? {icon: 'plus', title: 'Add a layout grid', run: addGrid} : null], {cls: (!mixed && !list().length) ? 'bare' : ''});
    if (mixed) { s.body.appendChild(h('p', {class: 'hd-note', text: 'These frames have different layout grids. Press + to give them all the same one.'})); return; }
    list().forEach((gd, i) => {
      const cur = () => list()[i] || fresh('grid'), upd = (patch, g) => { const a = list().slice(); if (i < a.length) { a[i] = Object.assign({}, a[i], patch); setList(a, g); } };
      const main = () => (cur().type === 'grid' ? 'size' : 'count');
      const tsel = ui.select([['grid', 'Grid'], ['columns', 'Columns'], ['rows', 'Rows']], () => cur().type || 'grid', v => { const a = list().slice(); a[i] = fresh(v, a[i]); setList(a); panel(); }, 'Layout grid type');
      const nf = ui.numField({label: gd.type === 'grid' ? 'Size' : 'Count', title: gd.type === 'grid' ? 'Grid size' : gd.type === 'rows' ? 'Number of rows' : 'Number of columns', min: 1, max: gd.type === 'grid' ? 2000 : 200, wide: true,
        get: () => num(+cur()[main()], gd.type === 'grid' ? 10 : 5), set: (v, g) => upd({[main()]: Math.max(1, Math.round(v))}, g)});
      const line = h('div', {class: 'hdv-grid' + (gd.visible === false ? ' off' : '')});
      const more = ib('sliders', 'Layout grid settings', () => {
        const body = h('div', {class: 'hdv-pop'}), f = (key, label, o) => ui.numField(Object.assign({label: label, title: label, wide: true, min: 0, get: () => num(+cur()[key], 0), set: (v, g) => upd({[key]: v}, g)}, o || {}));
        body.appendChild(h('div', {class: 'hd-phead'}, h('span', {class: 'hd-ptitle', text: cur().type === 'grid' ? 'Grid' : cur().type === 'rows' ? 'Rows' : 'Columns'}), ib('close', 'Close', () => hp.close())));
        if (cur().type === 'grid') body.appendChild(ui.row(f('size', 'Size', {min: 1})));
        else {
          body.appendChild(ui.row(f('count', 'Count', {min: 1, max: 200}), f('gutter', 'Gutter')));
          body.appendChild(ui.row(f('margin', 'Margin'), f('size', cur().type === 'rows' ? 'Height' : 'Width', {off: () => !cur().align || cur().align === 'stretch'})));
          body.appendChild(ui.row(h('label', {class: 'hd-sfield grow'}, ui.select([['stretch', 'Stretch to fit'], ['start', cur().type === 'rows' ? 'From the top' : 'From the left'], ['center', 'In the middle'], ['end', cur().type === 'rows' ? 'From the bottom' : 'From the right']],
            () => cur().align || 'stretch', v => { const p = {align: v}; if (v !== 'stretch' && !(cur().size > 0)) p.size = 64; upd(p); HD.ui.refresh(); }, 'Where the ' + (cur().type === 'rows' ? 'rows' : 'columns') + ' sit'))));
        }
        body.appendChild(ui.colorLine({title: 'Grid colour', solidOnly: true, hide: false, level: 1, get: () => ({type: 'solid', color: cur().color || '#FF0000', opacity: cur().opacity === undefined ? 0.1 : cur().opacity}), set: (p, g) => upd({color: p.color, opacity: p.opacity}, g)}));
        const hp = ui.pop(line, body, {cls: 'hd-pop-fx', label: 'Layout grid settings', side: 'left'});
      });
      const eye = ib(gd.visible === false ? 'eyeoff' : 'eye', 'Show or hide this grid', () => { upd({visible: cur().visible === false}); panel(); });
      const rm = ib('minus', 'Remove this grid', () => { const a = list().slice(); a.splice(i, 1); setList(a); panel(); });
      for (const b of [more, eye, rm]) b.disabled = !edit;
      line.appendChild(h('label', {class: 'hd-sfield grow'}, tsel)); line.appendChild(nf); line.appendChild(more); line.appendChild(eye); line.appendChild(rm);
      s.body.appendChild(line);
    });
    if (list().length && !gridsOn) s.body.appendChild(h('p', {class: 'hd-note', text: 'Layout grids are hidden now. Press ' + ui.keysLabel('shift+g') + ' to show them.'}));
  }
  function shapeSection(el, ids) {
    const ui = HD.ui, h = ui.h;
    if (!ids.length || !canEdit()) return;
    const n0 = S().get(ids[0]), one = ids.length === 1, boolSel = one && isBool(n0), shape = one && (SHAPES[n0.type] || n0.type === 'VECTOR');
    const many = ids.length >= 2 && ids.some(id => { const t = typeOf(id); return t !== 'TEXT' && t !== 'LINE'; });
    const masked = one && (n0.mask === true || (n0.type === 'GROUP' && !isBool(n0) && S().children(ids[0]).length > 0 && P(S().children(ids[0])[0], 'mask') === true));
    if (!boolSel && !shape && !many && !masked) return;
    const s = ui.section(el, boolSel ? 'Boolean' : 'Shape'), row = h('div', {class: 'hdv-ops'});
    const btn = (text, title, run) => h('button', {class: 'hd-btn', type: 'button', text: text, title: title, on: {click: run}});
    if (boolSel || many) {
      const opts = (boolSel ? [] : [['', 'Combine…']]).concat([['union', 'Union'], ['subtract', 'Subtract'], ['intersect', 'Intersect'], ['exclude', 'Exclude']]);
      row.appendChild(ui.select(opts, () => { const n = S().get(ids[0]); return boolSel && n ? n.bool : ''; }, v => { if (v) bool(v); }, boolSel ? 'How the shapes are combined' : 'Combine the shapes'));
    }
    if (shape) row.appendChild(btn('Edit shape', 'Edit the points of this shape (Enter)', editShape));
    if (boolSel || many || (one && SHAPES[n0.type])) row.appendChild(btn('Flatten', 'Make one vector of it (' + ui.keysLabel('mod+e') + ')', flatten));
    row.appendChild(btn(masked ? 'Remove mask' : 'Use as mask', masked ? 'Stop masking' : 'Show the layers above only where this one is (' + ui.keysLabel('mod+alt+m') + ')', mask));
    s.body.appendChild(row);
    if (boolSel) s.body.appendChild(h('p', {class: 'hd-note', text: 'Fill, stroke and effects of this group style the result. The shapes inside stay editable.'}));
  }

  /* ================================================================== wiring */
  function patchMove(def) {
    if (!def || def.hdVector) return;
    def.hdVector = true;
    const dbl0 = def.dbl, key0 = def.key;
    def.dbl = function (e) {
      const ids = U().selIds(), cur = ids.length === 1 ? ids[0] : null;
      if (cur && typeOf(cur) === 'VECTOR' && canEdit() && R().hitTest(e.x, e.y, {deep: true}) === cur) { enter(cur); return undefined; }
      return dbl0 ? dbl0.call(this, e) : undefined;
    };
    def.key = function (ev) {
      if (ev.key === 'Enter' && !ev.shiftKey) { const ids = U().selIds(); if (ids.length === 1 && typeOf(ids[0]) === 'VECTOR' && canEdit() && enter(ids[0])) return true; }
      return key0 ? key0.call(this, ev) : false;
    };
  }
  let commandsDone = false;
  function registerCommands() {
    if (commandsDone || !HD.ui || !HD.ui.command) return;
    commandsDone = true;
    const c = HD.ui.command;
    c({id: 'shape.edit', label: 'Edit shape (points and curves)', group: 'Shape', edit: true, run: editShape});
    for (const op of ['union', 'subtract', 'intersect', 'exclude']) c({id: 'bool.' + op, label: OP_NAME[op] + ' selection', group: 'Shape', edit: true, run: () => bool(op)});
    c({id: 'shape.flatten', label: 'Flatten selection', group: 'Shape', keys: 'mod+e', edit: true, run: flatten});
    c({id: 'shape.mask', label: 'Use as mask', group: 'Shape', keys: 'mod+alt+m', edit: true, run: mask});
    c({id: 'view.rulers', label: 'Show or hide rulers and guides', group: 'View', keys: 'shift+r', run: () => setRulers(!rulersOn)});
    c({id: 'view.grids', label: 'Show or hide layout grids', group: 'View', keys: 'shift+g', run: () => setGrids(!gridsOn)});
    c({id: 'view.clearGuides', label: 'Remove all guides on this page', group: 'View', edit: true, when: () => guidesOf().length > 0, run: () => setGuides([], null, 'Remove guides')});
  }
  function init() {
    if (!HD.tools || !HD.store || !HD.render || !HD.render.geom) return;
    HD.tools.register('vedit', veditTool);
    HD.tools.onChange((name) => {
      if (!overlayOn) { overlayOn = true; R().addOverlay(overlay); Promise.resolve().then(registerCommands); }
      if (name === 'move') patchMove(TL().def);
    });
    window.addEventListener('pointerdown', onDown, true);
    window.addEventListener('keydown', onKeyCapture, true);
    window.addEventListener('keyup', (ev) => { if (ev.key === 'Alt' && altDown) { altDown = false; ev.preventDefault(); redraw(); } }, true);
    window.addEventListener('blur', () => { if (altDown) { altDown = false; redraw(); } });
    HD.store.on('change', (ev) => {
      if (!ev || !ev.ids) return;
      if (E && !E.mine && ev.ids.has(E.id)) resync();
      const props = ev.props && typeof ev.props.get === 'function' ? ev.props : null;
      if (props) for (const id of HD.sel.ids || []) { const ps = props.get(id); if (ps && typeof ps.has === 'function' && (ps.has('grids') || ps.has('bool') || ps.has('mask') || ps.has('type'))) { panel(); break; } }
      if (rulersOn && HD.sel.page && ev.ids.has(HD.sel.page)) redraw();
    });
    HD.store.on('load', () => { if (E) leave(); hoverGuide = -1; dragGuide = null; });
    HD.sel.on('change', () => { if (E && !(HD.sel.ids.length === 1 && HD.sel.ids[0] === E.id)) leave(); });
    if (window.HoolaTheme && window.HoolaTheme.onChange) window.HoolaTheme.onChange(() => { colors = null; redraw(); });
    try { window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { colors = null; redraw(); }); } catch (e) { /* old browser */ }
    R().showGrids = gridsOn;
    if (HD.ui) {
      if (HD.ui.designSection) { HD.ui.designSection(shapeSection); HD.ui.designSection(gridSection); }
      const M = HD.ui.registerMenu;
      M('context', (ids) => { if (ids.length !== 1 || !canEdit()) return null; const t = typeOf(ids[0]); return SHAPES[t] || t === 'VECTOR' ? {label: 'Edit shape', keys: 'enter', run: editShape} : null; });
      M('context', (ids) => (canEdit() && (ids.length >= 2 || (ids.length === 1 && typeOf(ids[0]) === 'GROUP')) ? {label: 'Combine shapes', sub: ['union', 'subtract', 'intersect', 'exclude'].map(op => ({label: OP_NAME[op], checked: ids.length === 1 && P(ids[0], 'bool') === op ? true : undefined, run: () => bool(op)}))} : null));
      M('context', (ids) => (canEdit() && ids.length && (ids.length >= 2 || isBool(S().get(ids[0])) || SHAPES[typeOf(ids[0])]) ? {label: 'Flatten', keys: 'mod+e', run: flatten} : null));
      M('context', (ids) => (canEdit() && ids.length ? {label: ids.length === 1 && P(ids[0], 'mask') === true ? 'Remove mask' : 'Use as mask', keys: 'mod+alt+m', run: mask} : null));
      M('view', '-');
      M('view', {label: 'Rulers and guides', keys: 'shift+r', get checked() { return rulersOn ? true : undefined; }, run: () => setRulers(!rulersOn)});
      M('view', {label: 'Layout grids', keys: 'shift+g', get checked() { return gridsOn ? true : undefined; }, run: () => setGrids(!gridsOn)});
    }
  }

  HD.vector = {
    edit: enter, leave: leave, toVector: toVector, editShape: editShape, bool: bool, flatten: flatten, mask: mask,
    get editing() { return E ? E.id : null; },
    get rulers() { return rulersOn; }, set rulers(v) { setRulers(v); },
    get grids() { return gridsOn; }, set grids(v) { setGrids(v); },
    guides: guidesOf, setGuides(list) { if (guard()) setGuides((list || []).filter(g => g && (g.axis === 'x' || g.axis === 'y') && typeof g.pos === 'number').map(g => ({axis: g.axis, pos: g.pos})), null, 'Guides'); },
    model: {toModel: toModel, toD: toD, rebox: rebox, frameMat: frameMat},
    /* for tests: what the edit mode holds right now, with the points in SCREEN pixels of the canvas */
    debug() { if (!E) return null; const m = mw(); return {id: E.id, sel: Array.from(E.sel), subs: E.subs.map(s => ({closed: s.closed, pts: s.pts.map(p => ({s: toScr(m, p.x, p.y), i: p.i ? toScr(m, p.i[0], p.i[1]) : null, o: p.o ? toScr(m, p.o[0], p.o[1]) : null, sm: p.sm}))}))}; },
    gradientHandles() { const g = livePaint(); if (!g) return null; const q = gradPts(g); return {from: q.a, to: q.b, stops: q.stops.map(s => [s.x, s.y])}; }
  };
  init();
})();

/* HOOLA DESIGN - the renderer (docs/HOOLA_DESIGN_PLAN.md section 3, HD.render).
   One <canvas>, never a DOM node per layer. Built for speed:
   - one requestAnimationFrame loop that only works when something is dirty;
   - the document is painted into a hidden SCENE canvas; the visible canvas = scene + labels + overlays, so a moving
     cursor / selection box never repaints a layer;
   - a pan moves the scene bitmap and paints only the strips that came into view; an edit repaints only the
     rectangles that changed (old place + new place); everything else is a full repaint;
   - viewport culling by cached subtree extents, level of detail for tiny nodes, a bitmap cache for heavy subtrees
     (LRU, capped) that is only ever shown when its content version still matches;
   - the settled picture is always exact: a cached bitmap is used 1:1 or not at all once the view rests.
   Plain browser JS, no dependencies, no eval. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const L = HD.layout;
  const G = L.prop;
  const TAU = Math.PI * 2, DEG = Math.PI / 180, EPS = 0.01;
  const S = () => HD.store;
  const now = () => performance.now();
  function num(v, d) { return typeof v === 'number' && v === v && v !== Infinity && v !== -Infinity ? v : d; }
  function W(n) { return num(n.w, 100); }
  function H(n) { return n.type === 'LINE' ? 0 : num(n.h, 100); }

  const CONT = {PAGE: 1, FRAME: 1, GROUP: 1, SECTION: 1, COMPONENT: 1, COMPONENT_SET: 1, INSTANCE: 1};
  const TOPC = {FRAME: 1, SECTION: 1, COMPONENT: 1, COMPONENT_SET: 1};
  const LABELED = {FRAME: 1, SECTION: 1, COMPONENT: 1, COMPONENT_SET: 1, INSTANCE: 1};
  const GEO_MASK = {RECT: 1, ELLIPSE: 1, POLYGON: 1, STAR: 1, VECTOR: 1};
  const BLEND = {normal: 'source-over', pass: 'source-over', multiply: 'multiply', screen: 'screen', overlay: 'overlay', darken: 'darken',
    lighten: 'lighten', 'color-dodge': 'color-dodge', 'color-burn': 'color-burn', 'hard-light': 'hard-light', 'soft-light': 'soft-light',
    difference: 'difference', exclusion: 'exclusion', hue: 'hue', saturation: 'saturation', color: 'color', luminosity: 'luminosity',
    'plus-lighter': 'lighter', lighter: 'lighter'};
  /* property classes: what a change to them can touch */
  const NONVIS = {name: 1, locked: 1, cons: 1, reactions: 1, exports: 1, desc: 1, protoStart: 1, scroll: 1, fixed: 1, grids: 1,
    sizeH: 0, sizeV: 0, layoutPos: 1, minW: 1, maxW: 1, minH: 1, maxH: 1, layout: 1};
  const POSONLY = {x: 1, y: 1, rot: 1, flipH: 1, flipV: 1, parent: 1, idx: 1, visible: 1, opacity: 1, blend: 1, mask: 1};
  const F_FX = 1, F_BG = 2, F_INST = 4, F_TEXT = 8, F_IMG = 16, F_MASKKID = 32, F_BLENDKID = 64, F_UP = F_BG | F_INST | F_IMG | F_TEXT | F_BLENDKID;
  function blends(n) { const b = n.blend; return b !== undefined && b !== 'normal' && b !== 'pass' && BLEND[b] !== undefined && BLEND[b] !== 'source-over'; }
  const HAS_FILTER = (function () { try { const c = document.createElement('canvas').getContext('2d'); return typeof c.filter === 'string'; } catch (e) { return false; } })();
  const HAS_RR = typeof CanvasRenderingContext2D !== 'undefined' && typeof CanvasRenderingContext2D.prototype.roundRect === 'function';
  const HAS_CONIC = typeof CanvasRenderingContext2D !== 'undefined' && typeof CanvasRenderingContext2D.prototype.createConicGradient === 'function';
  const NODASH = [];
  const FAR = 30000;                       /* how far off-canvas a shape is drawn when only its shadow is wanted */

  /* ------------------------------------------------------------------ state */
  let canvas = null, vctx = null, scene = null, sctx = null, dpr = 1, cssW = 0, cssH = 0, ro = null;
  const view = {x: 0, y: 0, zoom: 1};
  const overlays = [];
  const listeners = {view: [], frame: []};
  const debug = {noCache: false, noBlit: false, noDirty: false, noLod: false, showDamage: false};
  let raf = 0, anim = null, sceneFull = true, overlayDirty = true, wantExact = false, settleTimer = 0;
  let last = {s: 0, tx: 0, ty: 0, page: null, w: 0, h: 0, valid: false};
  let serial = 1, clock = 1, compEpoch = 1, resEpoch = 1, imgEpoch = 1, instSeen = false, lastZoomAt = 0, lastChangeAt = 0;
  let editingId = null, pruneDue = false, lastFullMs = 0, lastRealAt = 0, forceReal = false, zoomTimer = 0, pvScale = 0;
  const pending = new Set();               /* node ids changed since the last paint */
  const gridIds = new Set();               /* frames that carry layout grids (drawn over the scene, never into it or an export) */
  let gridScan = true;
  let damage = [];                         /* world rects [x0,y0,x1,y1] that were painted on and are now stale */
  const stats = {ms: 0, nodes: 0, culled: 0, flat: 0, blits: 0, built: 0, layers: 0, mode: '', frames: 0, cacheMB: 0, cacheN: 0, regions: 0};
  let labelRects = [];

  /* ------------------------------------------------------------------ colours, paints */
  const colCache = new Map();
  function rgba(color, a) {
    if (a === undefined || a === null) a = 1;
    if (typeof color !== 'string') color = '#000000';
    if (a >= 1 && color.length === 7 && color.charCodeAt(0) === 35) return color;
    const k = color + '|' + a;
    let v = colCache.get(k);
    if (v !== undefined) return v;
    v = color;
    if (color.charCodeAt(0) === 35) {
      let r = 0, g = 0, b = 0, al = 1;
      const hx = color.slice(1);
      if (hx.length === 3 || hx.length === 4) {
        r = parseInt(hx[0] + hx[0], 16); g = parseInt(hx[1] + hx[1], 16); b = parseInt(hx[2] + hx[2], 16);
        if (hx.length === 4) al = parseInt(hx[3] + hx[3], 16) / 255;
      } else if (hx.length >= 6) {
        r = parseInt(hx.slice(0, 2), 16); g = parseInt(hx.slice(2, 4), 16); b = parseInt(hx.slice(4, 6), 16);
        if (hx.length >= 8) al = parseInt(hx.slice(6, 8), 16) / 255;
      }
      v = 'rgba(' + (r || 0) + ',' + (g || 0) + ',' + (b || 0) + ',' + Math.round(Math.max(0, Math.min(1, a * al)) * 1000) / 1000 + ')';
    }
    if (colCache.size > 5000) colCache.clear();
    colCache.set(k, v);
    return v;
  }
  function vis(p) { return p !== null && typeof p === 'object' && p.visible !== false && (p.opacity === undefined || p.opacity > 0); }
  function anyVis(a) { for (let i = 0; i < a.length; i++) if (vis(a[i])) return true; return false; }
  function countVis(a) { let c = 0; for (let i = 0; i < a.length; i++) if (vis(a[i])) c++; return c; }
  const gradCache = new WeakMap();
  /* A radial / sweep gradient is defined in the 0..1 space of the box, so in a box that is not square it is an ELLIPSE
     (a sweep is stretched the same way). The canvas only makes round ones: for such a box the gradient is built in unit
     space (unit: true) and must be painted with the box's scale on the context (unitFill / maskDraw do that). */
  function unitGrad(p, w, h) { return (p.type === 'radial' || p.type === 'angular') && w > EPS && h > EPS && Math.abs(w - h) > 0.01 * Math.max(w, h); }
  function gradient(ctx, p, w, h) {
    const c = gradCache.get(p);
    if (c !== undefined && c.w === w && c.h === h) return c.g;
    const stops = Array.isArray(p.stops) && p.stops.length ? p.stops : [{pos: 0, color: '#000000'}, {pos: 1, color: '#FFFFFF'}];
    let g = null;
    const lin = p.type === 'linear', unit = unitGrad(p, w, h), uw = unit ? 1 : w, uh = unit ? 1 : h;
    const f = Array.isArray(p.from) ? p.from : (lin ? [0.5, 0] : [0.5, 0.5]);
    const t = Array.isArray(p.to) ? p.to : (lin ? [0.5, 1] : [1, 0.5]);
    const fx = num(+f[0], 0.5) * uw, fy = num(+f[1], 0) * uh, tx = num(+t[0], 0.5) * uw, ty = num(+t[1], 1) * uh;
    try {
      if (lin) g = ctx.createLinearGradient(fx, fy, tx, ty);
      else if (p.type === 'radial') g = ctx.createRadialGradient(fx, fy, 0, fx, fy, Math.max(unit ? 1e-5 : 0.01, Math.hypot(tx - fx, ty - fy)));
      else if (HAS_CONIC) g = ctx.createConicGradient(Math.atan2(ty - fy, tx - fx), fx, fy);
      if (g) for (let i = 0; i < stops.length; i++) { const s = stops[i]; if (s) g.addColorStop(Math.max(0, Math.min(1, num(+s.pos, 0))), rgba(s.color, s.opacity)); }
    } catch (e) { g = null; }
    if (!g) g = rgba((stops[0] && stops[0].color) || '#000000', stops[0] && stops[0].opacity);
    gradCache.set(p, {w, h, g});
    return g;
  }
  /* set the fill (or stroke) style + alpha for one paint; false = nothing to draw with */
  function usePaint(ctx, p, w, h, alpha, stroke) {
    let st;
    if (p.type === 'solid' || p.type === undefined) { st = rgba(p.color, p.opacity); ctx.globalAlpha = alpha; }
    else if (p.type === 'linear' || p.type === 'radial' || p.type === 'angular') { st = gradient(ctx, p, w, h); ctx.globalAlpha = alpha * (p.opacity === undefined ? 1 : p.opacity); }
    else if (p.type === 'image') { st = '#D8D8DC'; ctx.globalAlpha = alpha * (p.opacity === undefined ? 1 : p.opacity); }
    else return false;
    if (stroke) ctx.strokeStyle = st; else ctx.fillStyle = st;
    return true;
  }
  function flatColor(n, depth) {
    const f = L.paints(n, 'fills');
    for (let i = f.length - 1; i >= 0; i--) {
      const p = f[i];
      if (!vis(p)) continue;
      if (p.type === 'solid' || p.type === undefined) return rgba(p.color, p.opacity);
      if (p.type === 'image') return '#C9C9CF';
      if (p.stops && p.stops[0]) return rgba(p.stops[0].color, (p.opacity === undefined ? 1 : p.opacity));
    }
    const s = L.paints(n, 'strokes');
    for (let i = s.length - 1; i >= 0; i--) if (vis(s[i]) && s[i].color) return rgba(s[i].color, s[i].opacity);
    return null;
  }

  /* ------------------------------------------------------------------ geometry */
  const LM = [1, 0, 0, 1, 0, 0];
  function localMat(n, out) {
    const x = num(n.x, 0), y = num(n.y, 0), rot = num(n.rot, 0), fh = n.flipH === true, fv = n.flipV === true;
    if (!rot && !fh && !fv) { out[0] = 1; out[1] = 0; out[2] = 0; out[3] = 1; out[4] = x; out[5] = y; return out; }
    const w = W(n), h = H(n), r = rot * DEG, cs = Math.cos(r), sn = Math.sin(r);
    const a = fh ? -cs : cs, b = fh ? -sn : sn, c = fv ? sn : -sn, d = fv ? -cs : cs, cx = w / 2, cy = h / 2;
    out[0] = a; out[1] = b; out[2] = c; out[3] = d; out[4] = x + cx - (a * cx + c * cy); out[5] = y + cy - (b * cx + d * cy);
    return out;
  }
  function mul(m, n) {
    return [m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1], m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
      m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5]];
  }
  function inv(m) {
    const det = m[0] * m[3] - m[1] * m[2];
    if (!det) return [1, 0, 0, 1, 0, 0];
    const a = m[3] / det, b = -m[1] / det, c = -m[2] / det, d = m[0] / det;
    return [a, b, c, d, -(a * m[4] + c * m[5]), -(b * m[4] + d * m[5])];
  }
  function worldMat(id) {
    const s = S(), chain = [];
    let c = id, g = 0;
    while (c && g++ < 2000) { const n = s.get(c); if (!n || n.type === 'PAGE' || n.type === 'DOCUMENT') break; chain.push(n); c = n.parent; }
    let m = [1, 0, 0, 1, 0, 0];
    for (let i = chain.length - 1; i >= 0; i--) m = mul(m, localMat(chain[i], [1, 0, 0, 1, 0, 0]));
    return m;
  }
  /* bounds of the rect (x0,y0)-(x1,y1) under m, into BX */
  const BX = [0, 0, 0, 0];
  function boxUnder(a, b, c, d, e, f, x0, y0, x1, y1) {
    if (b === 0 && c === 0) {
      let p = a * x0 + e, q = a * x1 + e;
      if (p > q) { const t = p; p = q; q = t; }
      BX[0] = p; BX[2] = q;
      p = d * y0 + f; q = d * y1 + f;
      if (p > q) { const t = p; p = q; q = t; }
      BX[1] = p; BX[3] = q;
      return;
    }
    const xa = a * x0 + c * y0, xb = a * x1 + c * y0, xc = a * x0 + c * y1, xd = a * x1 + c * y1;
    const ya = b * x0 + d * y0, yb = b * x1 + d * y0, yc = b * x0 + d * y1, yd = b * x1 + d * y1;
    BX[0] = Math.min(xa, xb, xc, xd) + e; BX[2] = Math.max(xa, xb, xc, xd) + e;
    BX[1] = Math.min(ya, yb, yc, yd) + f; BX[3] = Math.max(ya, yb, yc, yd) + f;
  }
  function radii(n, w, h) {
    const r = G(n, 'radius');
    if (r === undefined || r === null || r === 0) return null;
    const m = Math.min(w, h) / 2;
    if (typeof r === 'number') { const v = Math.max(0, Math.min(r, m)); return v > 0 ? [v, v, v, v] : null; }
    if (!Array.isArray(r)) return null;
    const o = [Math.max(0, +r[0] || 0), Math.max(0, +r[1] || 0), Math.max(0, +r[2] || 0), Math.max(0, +r[3] || 0)];
    if (!(o[0] || o[1] || o[2] || o[3])) return null;
    /* like CSS: shrink all corners together when two of them would overlap */
    const k = Math.min(1, w / Math.max(EPS, o[0] + o[1]), w / Math.max(EPS, o[3] + o[2]), h / Math.max(EPS, o[0] + o[3]), h / Math.max(EPS, o[1] + o[2]));
    if (k < 1) for (let i = 0; i < 4; i++) o[i] *= k;
    return o;
  }
  function rrect(p, x, y, w, h, r, grow) {
    if (w < 0) w = 0; if (h < 0) h = 0;
    let a = r[0], b = r[1], c = r[2], d = r[3];
    if (grow) { a = a > 0 ? Math.max(0, a + grow) : 0; b = b > 0 ? Math.max(0, b + grow) : 0; c = c > 0 ? Math.max(0, c + grow) : 0; d = d > 0 ? Math.max(0, d + grow) : 0; }
    const m = Math.min(w, h) / 2;
    if (a > m) a = m; if (b > m) b = m; if (c > m) c = m; if (d > m) d = m;
    if (HAS_RR && p.roundRect) { p.roundRect(x, y, w, h, [a, b, c, d]); return; }
    p.moveTo(x + a, y);
    p.lineTo(x + w - b, y); if (b) p.arcTo(x + w, y, x + w, y + b, b);
    p.lineTo(x + w, y + h - c); if (c) p.arcTo(x + w, y + h, x + w - c, y + h, c);
    p.lineTo(x + d, y + h); if (d) p.arcTo(x, y + h, x, y + h - d, d);
    p.lineTo(x, y + a); if (a) p.arcTo(x, y, x + a, y, a);
    p.closePath();
  }
  /* --- SVG path data: bounds (to scale a VECTOR's path to its box) */
  const bboxCache = new Map();
  function arcToCubics(x1, y1, rx, ry, phi, fa, fs, x2, y2, out) {
    rx = Math.abs(rx); ry = Math.abs(ry);
    if (!rx || !ry) { out.push([x1, y1, x2, y2, x2, y2]); return; }
    const sp = Math.sin(phi * DEG), cp = Math.cos(phi * DEG);
    const dx = (x1 - x2) / 2, dy = (y1 - y2) / 2, xp = cp * dx + sp * dy, yp = -sp * dx + cp * dy;
    const lam = (xp * xp) / (rx * rx) + (yp * yp) / (ry * ry);
    if (lam > 1) { const s = Math.sqrt(lam); rx *= s; ry *= s; }
    const rx2 = rx * rx, ry2 = ry * ry;
    let q = (rx2 * ry2 - rx2 * yp * yp - ry2 * xp * xp) / (rx2 * yp * yp + ry2 * xp * xp);
    q = Math.sqrt(Math.max(0, q)) * (fa === fs ? -1 : 1);
    const cxp = q * rx * yp / ry, cyp = -q * ry * xp / rx;
    const cx = cp * cxp - sp * cyp + (x1 + x2) / 2, cy = sp * cxp + cp * cyp + (y1 + y2) / 2;
    const ang = (ux, uy, vx, vy) => { const d = Math.hypot(ux, uy) * Math.hypot(vx, vy); let a = Math.acos(Math.max(-1, Math.min(1, (ux * vx + uy * vy) / (d || 1)))); if (ux * vy - uy * vx < 0) a = -a; return a; };
    const th1 = ang(1, 0, (xp - cxp) / rx, (yp - cyp) / ry);
    let dth = ang((xp - cxp) / rx, (yp - cyp) / ry, (-xp - cxp) / rx, (-yp - cyp) / ry);
    if (!fs && dth > 0) dth -= TAU; else if (fs && dth < 0) dth += TAU;
    const segs = Math.max(1, Math.ceil(Math.abs(dth) / (Math.PI / 2) - 1e-9)), dd = dth / segs, t = 4 / 3 * Math.tan(dd / 4);
    let px = x1, py = y1;
    for (let i = 0; i < segs; i++) {
      const a1 = th1 + i * dd, a2 = a1 + dd, c1 = Math.cos(a1), s1 = Math.sin(a1), c2 = Math.cos(a2), s2 = Math.sin(a2);
      const e1x = cx + cp * rx * c2 - sp * ry * s2, e1y = cy + sp * rx * c2 + cp * ry * s2;
      const d1x = -cp * rx * s1 - sp * ry * c1, d1y = -sp * rx * s1 + cp * ry * c1, d2x = -cp * rx * s2 - sp * ry * c2, d2y = -sp * rx * s2 + cp * ry * c2;
      out.push([px + t * d1x, py + t * d1y, e1x - t * d2x, e1y - t * d2y, e1x, e1y]);
      px = e1x; py = e1y;
    }
  }
  /* path data -> absolute segments ['M',x,y] ['L',x,y] ['C',x1,y1,x2,y2,x,y] ['Z'].
     Reads every SVG command (M L H V C S Q T A Z and the relative forms), numbers without separators ("1.5.5", "1-2",
     "1e-3"), arc flags written together ("a1 1 0 01 5 5") and repeated arguments; like a browser it keeps what came
     before the first thing it can not read. */
  const PATH_CMDS = 'MmLlHhVvCcSsQqTtAaZz';
  function parsePath(d) {
    const out = [], s = typeof d === 'string' ? d : '', n = s.length;
    let i = 0, cmd = '', cx = 0, cy = 0, sx = 0, sy = 0, lx = 0, ly = 0, lc = '', guard = 0, bad = false;
    const ws = () => { while (i < n) { const c = s.charCodeAt(i); if (c === 32 || c === 44 || (c >= 9 && c <= 13)) i++; else break; } };
    const nx = () => {
      ws();
      const st = i;
      let c = s.charCodeAt(i), dig = 0;
      if (c === 45 || c === 43) i++;
      while (i < n && (c = s.charCodeAt(i)) >= 48 && c <= 57) { i++; dig++; }
      if (i < n && s.charCodeAt(i) === 46) { i++; while (i < n && (c = s.charCodeAt(i)) >= 48 && c <= 57) { i++; dig++; } }
      if (!dig) { bad = true; i = st; return 0; }
      if (i < n && (s.charCodeAt(i) === 101 || s.charCodeAt(i) === 69)) {
        const save = i;
        let ed = 0;
        i++;
        if (i < n && (s.charCodeAt(i) === 45 || s.charCodeAt(i) === 43)) i++;
        while (i < n && (c = s.charCodeAt(i)) >= 48 && c <= 57) { i++; ed++; }
        if (!ed) i = save;
      }
      const v = +s.slice(st, i);
      return v === v && v !== Infinity && v !== -Infinity ? v : 0;
    };
    const flag = () => { ws(); const c = s.charCodeAt(i); if (c === 48 || c === 49) { i++; return c === 49 ? 1 : 0; } bad = true; return 0; };
    const more = () => { ws(); if (i >= n) return false; const c = s.charCodeAt(i); return (c >= 48 && c <= 57) || c === 46 || c === 45 || c === 43; };
    while (guard++ < 400000) {
      ws();
      if (i >= n) break;
      const ch = s.charAt(i);
      if (PATH_CMDS.indexOf(ch) >= 0) { cmd = ch; i++; }
      else if (!cmd || !more()) break;
      const rel = cmd === cmd.toLowerCase(), C = cmd.toUpperCase();
      const ox = rel ? cx : 0, oy = rel ? cy : 0;
      if (C === 'Z') { out.push(['Z']); cx = sx; cy = sy; lc = C; cmd = ''; continue; }
      if (!more()) break;
      const at = i, len = out.length;
      if (C === 'M') { cx = nx() + ox; cy = nx() + oy; sx = cx; sy = cy; out.push(['M', cx, cy]); cmd = rel ? 'l' : 'L'; }
      else if (C === 'L') { cx = nx() + ox; cy = nx() + oy; out.push(['L', cx, cy]); }
      else if (C === 'H') { cx = nx() + ox; out.push(['L', cx, cy]); }
      else if (C === 'V') { cy = nx() + oy; out.push(['L', cx, cy]); }
      else if (C === 'C') { const a = nx() + ox, b = nx() + oy, c = nx() + ox, e = nx() + oy, x = nx() + ox, y = nx() + oy; out.push(['C', a, b, c, e, x, y]); lx = c; ly = e; cx = x; cy = y; }
      else if (C === 'S') { const sm = lc === 'C' || lc === 'S', a = sm ? 2 * cx - lx : cx, b = sm ? 2 * cy - ly : cy, c = nx() + ox, e = nx() + oy, x = nx() + ox, y = nx() + oy; out.push(['C', a, b, c, e, x, y]); lx = c; ly = e; cx = x; cy = y; }
      else if (C === 'Q') { const qx = nx() + ox, qy = nx() + oy, x = nx() + ox, y = nx() + oy; out.push(['C', cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy), x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y), x, y]); lx = qx; ly = qy; cx = x; cy = y; }
      else if (C === 'T') { const sm = lc === 'Q' || lc === 'T', qx = sm ? 2 * cx - lx : cx, qy = sm ? 2 * cy - ly : cy, x = nx() + ox, y = nx() + oy; out.push(['C', cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy), x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y), x, y]); lx = qx; ly = qy; cx = x; cy = y; }
      else if (C === 'A') {
        const rx = nx(), ry = nx(), ph = nx(), fa = flag(), fs = flag(), x = nx() + ox, y = nx() + oy, cs = [];
        if (!bad) {
          if (Math.abs(x - cx) < 1e-12 && Math.abs(y - cy) < 1e-12) { /* an arc to where it starts draws nothing */ }
          else { arcToCubics(cx, cy, rx, ry, ph, fa, fs, x, y, cs); for (const q of cs) out.push(['C', q[0], q[1], q[2], q[3], q[4], q[5]]); }
          cx = x; cy = y;
        }
      }
      if (bad) { out.length = len; i = at; break; }       /* a half-written command is dropped, what came before stays */
      lc = C;
    }
    return out;
  }
  function pathBBox(d) {
    let r = bboxCache.get(d);
    if (r !== undefined) return r;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, closed = false, px = 0, py = 0;
    const pt = (x, y) => { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; };
    for (const sg of parsePath(d)) {
      if (sg[0] === 'Z') { closed = true; continue; }
      if (sg[0] !== 'C') { px = sg[1]; py = sg[2]; pt(px, py); continue; }
      pt(sg[5], sg[6]);
      for (let k = 0; k < 2; k++) {
        const p0 = k ? py : px, p1 = sg[1 + k], p2 = sg[3 + k], p3 = sg[5 + k];
        const A = -p0 + 3 * p1 - 3 * p2 + p3, B = 2 * (p0 - 2 * p1 + p2), C = p1 - p0, ts = [];
        if (Math.abs(A) < 1e-12) { if (Math.abs(B) > 1e-12) ts.push(-C / B); }
        else { const disc = B * B - 4 * A * C; if (disc >= 0) { const sq = Math.sqrt(disc); ts.push((-B + sq) / (2 * A), (-B - sq) / (2 * A)); } }
        for (const t of ts) if (t > 0 && t < 1) {
          const u = 1 - t, v = u * u * u * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t * t * t * p3;
          if (k) { if (v < y0) y0 = v; if (v > y1) y1 = v; } else { if (v < x0) x0 = v; if (v > x1) x1 = v; }
        }
      }
      px = sg[5]; py = sg[6];
    }
    r = x0 === Infinity ? {x0: 0, y0: 0, x1: 0, y1: 0, closed} : {x0, y0, x1, y1, closed};
    if (bboxCache.size > 4000) bboxCache.clear();
    bboxCache.set(d, r);
    return r;
  }
  /* the map that fits a VECTOR's path into the box it has now: [sx, sy, tx, ty, closed]. The contract says the path is
     written in the node's own 0..w / 0..h box; a path whose own bounds sit somewhere else (an imported one that starts
     at 40,40; one written for another size) is moved and scaled so that its bounds become the box. */
  function vecFit(d, w, h) {
    const b = pathBBox(d), bw = b.x1 - b.x0, bh = b.y1 - b.y0, tw = Math.max(0.02, 0.002 * w), th = Math.max(0.02, 0.002 * h);
    let sx = 1, sy = 1, tx = 0, ty = 0;
    if (bw > EPS && Math.abs(bw - w) > tw) sx = w / bw;
    if (bh > EPS && Math.abs(bh - h) > th) sy = h / bh;
    if (Math.abs(b.x0) > tw) tx = -b.x0 * sx;
    if (Math.abs(b.y0) > th) ty = -b.y0 * sy;
    return [sx, sy, tx, ty, b.closed];
  }
  /* the segments of a VECTOR as they are drawn: absolute, inside the node's box */
  function vectorSegs(n) {
    const d = typeof n.path === 'string' ? n.path : '', f = vecFit(d, W(n), H(n)), segs = parsePath(d);
    if (f[0] === 1 && f[1] === 1 && f[2] === 0 && f[3] === 0) return segs;
    for (const sg of segs) for (let i = 1; i < sg.length; i += 2) { sg[i] = sg[i] * f[0] + f[2]; sg[i + 1] = sg[i + 1] * f[1] + f[3]; }
    return segs;
  }
  function segsToD(segs) {
    let out = '';
    for (const sg of segs) {
      if (sg[0] === 'Z') out += 'Z';
      else if (sg[0] === 'C') out += 'C' + fnum(sg[1]) + ' ' + fnum(sg[2]) + ' ' + fnum(sg[3]) + ' ' + fnum(sg[4]) + ' ' + fnum(sg[5]) + ' ' + fnum(sg[6]);
      else out += sg[0] + fnum(sg[1]) + ' ' + fnum(sg[2]);
    }
    return out;
  }
  const pathCache = new Map();
  function cachePath(key, make) {
    let g = pathCache.get(key);
    if (g !== undefined) return g;
    g = make();
    if (pathCache.size > 3000) { let c = 0; for (const k of pathCache.keys()) { pathCache.delete(k); if (++c > 800) break; } }
    pathCache.set(key, g);
    return g;
  }
  function polyPoints(sides, ratio, star) {
    sides = Math.max(3, Math.min(60, Math.round(num(+sides, star ? 5 : 3))));
    ratio = Math.max(0.01, Math.min(1, num(+ratio, 0.5)));
    const N = star ? sides * 2 : sides, pts = [];
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (let i = 0; i < N; i++) {
      const a = -Math.PI / 2 + i * TAU / N, r = star && (i & 1) ? ratio : 1, x = Math.cos(a) * r, y = Math.sin(a) * r;
      pts.push(x, y);
      if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
    }
    for (let i = 0; i < pts.length; i += 2) { pts[i] = (pts[i] - x0) / (x1 - x0 || 1); pts[i + 1] = (pts[i + 1] - y0) / (y1 - y0 || 1); }
    return pts;
  }
  const R_RECT = 0, R_RR = 1, R_ELL = 2, R_PATH = 3, R_LINE = 4;
  const G_RECT = {k: R_RECT, r: null, p: null, rule: 'nonzero', open: false, inv: null};
  const G_ELL = {k: R_ELL, r: null, p: null, rule: 'nonzero', open: false, inv: null};
  const G_LINE = {k: R_LINE, r: null, p: null, rule: 'nonzero', open: true, inv: null};
  function geomOf(n, type, w, h, id, v, rec) {
    if (type === 'ELLIPSE') return G_ELL;
    if (type === 'BOOL') return boolGeom(n, id, v, rec);
    if (type === 'LINE') return G_LINE;
    if (type === 'VECTOR') {
      const d = typeof n.path === 'string' ? n.path : '';
      const rule = n.fillRule === 'evenodd' ? 'evenodd' : 'nonzero';
      return cachePath('V' + rule + '|' + w + '|' + h + '|' + d, () => {
        let p;
        const sc = vecFit(d, w, h);
        try { p = new Path2D(d); } catch (e) { p = new Path2D(); }
        if (sc[0] !== 1 || sc[1] !== 1 || sc[2] !== 0 || sc[3] !== 0) { const q = new Path2D(); try { q.addPath(p, new DOMMatrix([sc[0], 0, 0, sc[1], sc[2], sc[3]])); p = q; } catch (e) { /* as written */ } }
        return {k: R_PATH, r: null, p, rule, open: !sc[4], inv: null};
      });
    }
    if (type === 'POLYGON' || type === 'STAR') {
      const star = type === 'STAR', sides = G(n, 'sides'), ratio = star ? G(n, 'ratio') : 1;
      return cachePath('P' + (star ? 'S' : 'P') + sides + '|' + ratio + '|' + w + '|' + h, () => {
        const pts = polyPoints(sides, ratio, star), p = new Path2D();
        for (let i = 0; i < pts.length; i += 2) { if (i) p.lineTo(pts[i] * w, pts[i + 1] * h); else p.moveTo(pts[i] * w, pts[i + 1] * h); }
        p.closePath();
        return {k: R_PATH, r: null, p, rule: 'nonzero', open: false, inv: null, pts};
      });
    }
    const r = radii(n, w, h);
    return r === null ? G_RECT : {k: R_RR, r, p: null, rule: 'nonzero', open: false, inv: null};
  }
  function inversePath(g) {
    if (g.inv) return g.inv;
    const q = new Path2D();
    q.rect(-1e6, -1e6, 2e6, 2e6);
    q.addPath(g.p);
    g.inv = q;
    return q;
  }
  /* add the outline (grown by `grow`) as one closed subpath to p (a context or a Path2D) */
  function traceGeom(p, g, w, h, grow) {
    switch (g.k) {
      case R_RECT: p.rect(-grow, -grow, Math.max(0, w + 2 * grow), Math.max(0, h + 2 * grow)); break;
      case R_RR: rrect(p, -grow, -grow, w + 2 * grow, h + 2 * grow, g.r, grow); break;
      case R_ELL: p.ellipse(w / 2, h / 2, Math.max(0, w / 2 + grow), Math.max(0, h / 2 + grow), 0, 0, TAU); p.closePath(); break;
      default: break;
    }
  }
  function fillGeom(ctx, g, w, h, grow) {
    switch (g.k) {
      case R_RECT: if (grow) ctx.fillRect(-grow, -grow, w + 2 * grow, h + 2 * grow); else ctx.fillRect(0, 0, w, h); break;
      case R_RR: ctx.beginPath(); rrect(ctx, -grow, -grow, w + 2 * grow, h + 2 * grow, g.r, grow); ctx.fill(); break;
      case R_ELL: ctx.beginPath(); ctx.ellipse(w / 2, h / 2, Math.max(0, w / 2 + grow), Math.max(0, h / 2 + grow), 0, 0, TAU); ctx.fill(); break;
      case R_PATH: ctx.fill(g.p, g.rule); break;
      default: break;
    }
  }
  function clipGeom(ctx, g, w, h) {
    if (g.k === R_PATH) { ctx.clip(g.p, g.rule); return; }
    ctx.beginPath();
    traceGeom(ctx, g, w, h, 0);
    ctx.clip();
  }
  function strokeGeom(ctx, g, w, h, sw, align) {
    const o = align === 'inside' ? -sw / 2 : align === 'outside' ? sw / 2 : 0;
    switch (g.k) {
      case R_RECT:
        if (o < 0 && (w <= sw || h <= sw)) { ctx.fillStyle = ctx.strokeStyle; ctx.fillRect(0, 0, w, h); }
        else { ctx.lineWidth = sw; ctx.strokeRect(-o, -o, w + 2 * o, h + 2 * o); }
        break;
      case R_RR:
        ctx.beginPath();
        if (o < 0 && (w <= sw || h <= sw)) { rrect(ctx, 0, 0, w, h, g.r, 0); ctx.fillStyle = ctx.strokeStyle; ctx.fill(); }
        else { rrect(ctx, -o, -o, w + 2 * o, h + 2 * o, g.r, o); ctx.lineWidth = sw; ctx.stroke(); }
        break;
      case R_ELL:
        ctx.beginPath();
        if (o < 0 && (w <= sw || h <= sw)) { ctx.ellipse(w / 2, h / 2, w / 2, h / 2, 0, 0, TAU); ctx.fillStyle = ctx.strokeStyle; ctx.fill(); }
        else { ctx.ellipse(w / 2, h / 2, Math.max(0, w / 2 + o), Math.max(0, h / 2 + o), 0, 0, TAU); ctx.lineWidth = sw; ctx.stroke(); }
        break;
      case R_PATH:
        if (o === 0 || g.open) { ctx.lineWidth = sw; ctx.stroke(g.p); }
        else {
          ctx.save();
          if (o < 0) ctx.clip(g.p, g.rule); else ctx.clip(inversePath(g), 'evenodd');
          ctx.lineWidth = sw * 2; ctx.stroke(g.p);
          ctx.restore();
        }
        break;
      case R_LINE: ctx.lineWidth = sw; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(w, 0); ctx.stroke(); break;
      default: break;
    }
  }

  /* ------------------------------------------------------------------ outlines as segments, boolean groups */
  const KAPPA = 0.5522847498307936;
  /* the outline of a shape as absolute segments in its own box (what a boolean, "Flatten" and "Edit shape" work on) */
  function outlineSegs(n, type, w, h) {
    if (type === 'VECTOR') return {segs: vectorSegs(n), rule: n.fillRule === 'evenodd' ? 'evenodd' : 'nonzero'};
    const out = [];
    if (type === 'LINE') { out.push(['M', 0, 0], ['L', w, 0]); return {segs: out, rule: 'nonzero', open: true}; }
    if (type === 'ELLIPSE') {
      const rx = w / 2, ry = h / 2, kx = rx * KAPPA, ky = ry * KAPPA;
      out.push(['M', w, ry], ['C', w, ry + ky, rx + kx, h, rx, h], ['C', rx - kx, h, 0, ry + ky, 0, ry], ['C', 0, ry - ky, rx - kx, 0, rx, 0], ['C', rx + kx, 0, w, ry - ky, w, ry], ['Z']);
      return {segs: out, rule: 'nonzero'};
    }
    if (type === 'POLYGON' || type === 'STAR') {
      const pts = polyPoints(G(n, 'sides'), type === 'STAR' ? G(n, 'ratio') : 1, type === 'STAR');
      for (let i = 0; i < pts.length; i += 2) out.push([i ? 'L' : 'M', pts[i] * w, pts[i + 1] * h]);
      out.push(['Z']);
      return {segs: out, rule: 'nonzero'};
    }
    const r = radii(n, w, h) || [0, 0, 0, 0], a = r[0], b = r[1], c = r[2], d = r[3], k = 1 - KAPPA;
    out.push(['M', a, 0], ['L', w - b, 0]);
    if (b) out.push(['C', w - b * k, 0, w, b * k, w, b]);
    out.push(['L', w, h - c]);
    if (c) out.push(['C', w, h - c * k, w - c * k, h, w - c, h]);
    out.push(['L', d, h]);
    if (d) out.push(['C', d * k, h, 0, h - d * k, 0, h - d]);
    out.push(['L', 0, a]);
    if (a) out.push(['C', 0, a * k, a * k, 0, a, 0]);
    out.push(['Z']);
    return {segs: out, rule: 'nonzero'};
  }
  const BOOL = {union: 1, subtract: 1, intersect: 1, exclude: 1};
  const BTOL = 0.02;                       /* a curve is cut into straight pieces no further than this from it (in layer units) */
  /* GROUP + bool = one shape: its own fills / strokes / effects style the RESULT of its children's outlines */
  function dtype(n) { return n.type === 'GROUP' && n.bool !== undefined && BOOL[n.bool] === 1 ? 'BOOL' : n.type; }
  function boolKids(id, v) {
    const out = [];
    if (v !== null && v !== undefined) { for (let i = 0; i < v.kids.length; i++) out.push({n: v.kids[i].n, id: v.kids[i].key, v: v.kids[i]}); return out; }
    const s = S(), ks = s.children(id);
    for (let i = 0; i < ks.length; i++) { const cn = s.get(ks[i]); if (cn) out.push({n: cn, id: ks[i], v: null}); }
    return out;
  }
  /* a node as an operand: {op, kids} or a leaf {a, b: index range of its curves, rule, box} */
  function operandOf(n, id, v, m, depth, W0) {
    if (n.visible === false || depth > 12) return null;
    const type = n.type;
    const lm = mul(m, localMat(n, [1, 0, 0, 1, 0, 0]));
    if (type === 'GROUP') {
      const kids = boolKids(id, v), ops = [];
      for (const k of kids) { const o = operandOf(k.n, k.id, k.v, lm, depth + 1, W0); if (o) ops.push(o); }
      if (!ops.length) return null;
      return ops.length === 1 ? ops[0] : {op: BOOL[n.bool] === 1 ? n.bool : 'union', kids: ops};
    }
    if (type === 'TEXT' || type === 'LINE') return null;        /* no area of their own: they take no part */
    const o = outlineSegs(n, type, W(n), H(n));
    return leafOf(o.segs, o.rule, lm, W0);
  }
  function leafOf(segs, rule, m, W0) {
    const cv = W0.curves, a = cv.length;
    let px = 0, py = 0, sx = 0, sy = 0, open = false;
    const X = (x, y) => m[0] * x + m[2] * y + m[4], Y = (x, y) => m[1] * x + m[3] * y + m[5];
    const line = (x0, y0, x1, y1) => { if (Math.abs(x0 - x1) > 1e-9 || Math.abs(y0 - y1) > 1e-9) cv.push([x0, y0, x1, y1]); };
    const close = () => { if (open) line(px, py, sx, sy); open = false; };
    for (const sg of segs) {
      if (sg[0] === 'M') { close(); px = sx = X(sg[1], sg[2]); py = sy = Y(sg[1], sg[2]); }
      else if (sg[0] === 'L') { const x = X(sg[1], sg[2]), y = Y(sg[1], sg[2]); line(px, py, x, y); px = x; py = y; open = true; }
      else if (sg[0] === 'C') {
        const x1 = X(sg[1], sg[2]), y1 = Y(sg[1], sg[2]), x2 = X(sg[3], sg[4]), y2 = Y(sg[3], sg[4]), x = X(sg[5], sg[6]), y = Y(sg[5], sg[6]);
        if (Math.abs((x1 - px) * (y - py) - (y1 - py) * (x - px)) < 1e-9 && Math.abs((x2 - px) * (y - py) - (y2 - py) * (x - px)) < 1e-9 && (x1 - px) * (x - x1) + (y1 - py) * (y - y1) >= 0 && (x2 - x1) * (x - x2) + (y2 - y1) * (y - y2) >= 0 && (x2 - x1) * (x - px) + (y2 - y1) * (y - py) >= 0) line(px, py, x, y);
        else cv.push([px, py, x1, y1, x2, y2, x, y]);
        px = x; py = y; open = true;
      } else if (sg[0] === 'Z') { close(); px = sx; py = sy; }
    }
    close();
    if (cv.length === a) return null;
    return {a, b: cv.length, rule, e0: 0, e1: 0, x0: 0, y0: 0, x1: 0, y1: 0};
  }
  function cubicAt(c, t) {
    const u = 1 - t, a = u * u * u, b = 3 * u * u * t, d = 3 * u * t * t, e = t * t * t;
    return [a * c[0] + b * c[2] + d * c[4] + e * c[6], a * c[1] + b * c[3] + d * c[5] + e * c[7]];
  }
  function blossom(p0, p1, p2, p3, u, v, w) {
    const a = p0 + (p1 - p0) * u, b = p1 + (p2 - p1) * u, c = p2 + (p3 - p2) * u, d = a + (b - a) * v, e = b + (c - b) * v;
    return d + (e - d) * w;
  }
  function insideLeaf(lf, E, x, y) {
    if (x < lf.x0 || x > lf.x1 || y < lf.y0 || y > lf.y1) return false;
    let wn = 0;
    for (let i = lf.e0; i < lf.e1; i += 4) {
      const y0 = E[i + 1], y1 = E[i + 3];
      if (y0 <= y) { if (y1 > y && (E[i + 2] - E[i]) * (y - y0) - (x - E[i]) * (y1 - y0) > 0) wn++; }
      else if (y1 <= y && (E[i + 2] - E[i]) * (y - y0) - (x - E[i]) * (y1 - y0) < 0) wn--;
    }
    return lf.rule === 'evenodd' ? (wn & 1) !== 0 : wn !== 0;
  }
  function insideOp(o, E, x, y) {
    if (o.op === undefined) return insideLeaf(o, E, x, y);
    const ks = o.kids;
    if (o.op === 'union') { for (let i = 0; i < ks.length; i++) if (insideOp(ks[i], E, x, y)) return true; return false; }
    if (o.op === 'intersect') { for (let i = 0; i < ks.length; i++) if (!insideOp(ks[i], E, x, y)) return false; return true; }
    if (o.op === 'subtract') { if (!insideOp(ks[0], E, x, y)) return false; for (let i = 1; i < ks.length; i++) if (insideOp(ks[i], E, x, y)) return false; return true; }
    let c = false;
    for (let i = 0; i < ks.length; i++) if (insideOp(ks[i], E, x, y)) c = !c;
    return c;
  }
  /* The real outline of a boolean: every curve is cut into short straight pieces, the pieces are cut where they cross,
     a piece stays when the result is inside on one side of it and outside on the other, the kept pieces are chained
     into closed loops and written back as the ORIGINAL curves between the crossings (so the result is curves, not a
     polygon). Crossings are found on the straight pieces: they are right to about BTOL of a layer unit. */
  function boolCompute(root, curves) {
    const E = [];                                   /* the uncut pieces of every leaf, 4 numbers each: for the inside test */
    const P = [];                                   /* pieces: [x0, y0, x1, y1, curve, t0, t1] */
    const flat = (lf) => {
      lf.e0 = E.length;
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (let ci = lf.a; ci < lf.b; ci++) {
        const c = curves[ci];
        let N = 1;
        if (c.length === 8) {
          const dd = Math.max(Math.hypot(c[0] - 2 * c[2] + c[4], c[1] - 2 * c[3] + c[5]), Math.hypot(c[2] - 2 * c[4] + c[6], c[3] - 2 * c[5] + c[7]));
          N = Math.max(1, Math.min(400, Math.ceil(Math.sqrt(0.75 * dd / BTOL))));
        }
        let px = c[0], py = c[1];
        for (let k = 1; k <= N; k++) {
          const q = c.length === 8 ? (k === N ? [c[6], c[7]] : cubicAt(c, k / N)) : [c[2], c[3]];
          if (px !== q[0] || py !== q[1]) { E.push(px, py, q[0], q[1]); P.push([px, py, q[0], q[1], ci, (k - 1) / N, k / N]); }
          if (px < x0) x0 = px; if (px > x1) x1 = px; if (py < y0) y0 = py; if (py > y1) y1 = py;
          px = q[0]; py = q[1];
        }
        if (px < x0) x0 = px; if (px > x1) x1 = px; if (py < y0) y0 = py; if (py > y1) y1 = py;
      }
      lf.e1 = E.length; lf.x0 = x0; lf.y0 = y0; lf.x1 = x1; lf.y1 = y1;
    };
    const walk = (o) => { if (o.op === undefined) flat(o); else for (const k of o.kids) walk(k); };
    walk(root);
    const n = P.length;
    if (!n || n > 60000) return null;
    /* cut the pieces where they cross or lie on each other */
    const order = [];
    for (let i = 0; i < n; i++) order.push(i);
    const minX = (p) => (p[0] < p[2] ? p[0] : p[2]), maxX = (p) => (p[0] > p[2] ? p[0] : p[2]);
    order.sort((a, b) => minX(P[a]) - minX(P[b]));
    const cuts = new Array(n);
    const cut = (i, s, x, y) => { if (s > 1e-9 && s < 1 - 1e-9) (cuts[i] || (cuts[i] = [])).push([s, x, y]); };
    for (let oi = 0; oi < n; oi++) {
      const i = order[oi], a = P[i], ax1 = maxX(a), ay0 = Math.min(a[1], a[3]), ay1 = Math.max(a[1], a[3]);
      const rx = a[2] - a[0], ry = a[3] - a[1], rr = rx * rx + ry * ry;
      for (let oj = oi + 1; oj < n; oj++) {
        const j = order[oj], b = P[j];
        if (minX(b) > ax1 + 1e-9) break;
        if (Math.min(b[1], b[3]) > ay1 + 1e-9 || Math.max(b[1], b[3]) < ay0 - 1e-9) continue;
        const sx = b[2] - b[0], sy = b[3] - b[1], qx = b[0] - a[0], qy = b[1] - a[1];
        const den = rx * sy - ry * sx, ss = sx * sx + sy * sy;
        if (Math.abs(den) > 1e-12 * Math.sqrt(rr * ss)) {
          const t = (qx * sy - qy * sx) / den, u = (qx * ry - qy * rx) / den;
          if (t < -1e-9 || t > 1 + 1e-9 || u < -1e-9 || u > 1 + 1e-9) continue;
          /* one point for both, so the two cuts meet exactly; an end point keeps its own coordinates */
          let x = a[0] + t * rx, y = a[1] + t * ry;
          if (t <= 1e-9) { x = a[0]; y = a[1]; } else if (t >= 1 - 1e-9) { x = a[2]; y = a[3]; } else if (u <= 1e-9) { x = b[0]; y = b[1]; } else if (u >= 1 - 1e-9) { x = b[2]; y = b[3]; }
          cut(i, t, x, y); cut(j, u, x, y);
        } else if (Math.abs(qx * ry - qy * rx) <= 1e-9 * Math.sqrt(rr)) {
          /* on one line: each is cut at the other's ends */
          const t0 = (qx * rx + qy * ry) / rr, t1 = ((b[2] - a[0]) * rx + (b[3] - a[1]) * ry) / rr;
          cut(i, t0, b[0], b[1]); cut(i, t1, b[2], b[3]);
          cut(j, (-qx * sx - qy * sy) / ss, a[0], a[1]); cut(j, ((a[2] - b[0]) * sx + (a[3] - b[1]) * sy) / ss, a[2], a[3]);
        }
      }
    }
    /* keep the pieces that lie on the edge of the result, the inside on their left */
    const kept = [], seen = new Set();
    const key = (x, y) => Math.round(x * 1e5) + ',' + Math.round(y * 1e5);
    const take = (x0, y0, x1, y1, ci, t0, t1) => {
      const dx = x1 - x0, dy = y1 - y0, len = Math.hypot(dx, dy);
      if (len < 1e-7) return;
      const mx = (x0 + x1) / 2, my = (y0 + y1) / 2, d = Math.min(2e-3, len * 0.25), nx = -dy / len * d, ny = dx / len * d;
      const l = insideOp(root, E, mx + nx, my + ny), r = insideOp(root, E, mx - nx, my - ny);
      if (l === r) return;
      const pc = l ? [x0, y0, x1, y1, ci, t0, t1] : [x1, y1, x0, y0, ci, t1, t0];
      const k = key(pc[0], pc[1]) + '>' + key(pc[2], pc[3]);
      if (seen.has(k)) return;
      seen.add(k);
      kept.push(pc);
    };
    for (let i = 0; i < n; i++) {
      const p = P[i], cs = cuts[i];
      if (!cs) { take(p[0], p[1], p[2], p[3], p[4], p[5], p[6]); continue; }
      cs.sort((u, v) => u[0] - v[0]);
      let s0 = 0, x0 = p[0], y0 = p[1];
      for (let k = 0; k <= cs.length; k++) {
        const s1 = k < cs.length ? cs[k][0] : 1, x1 = k < cs.length ? cs[k][1] : p[2], y1 = k < cs.length ? cs[k][2] : p[3];
        if (s1 - s0 > 1e-9) take(x0, y0, x1, y1, p[4], p[5] + s0 * (p[6] - p[5]), p[5] + s1 * (p[6] - p[5]));
        s0 = s1; x0 = x1; y0 = y1;
      }
    }
    if (!kept.length) return {d: '', n: 0};
    /* chain into loops */
    const from = new Map();
    for (let i = 0; i < kept.length; i++) { const k = key(kept[i][0], kept[i][1]); let l = from.get(k); if (!l) { l = []; from.set(k, l); } l.push(i); }
    const used = new Uint8Array(kept.length), loops = [];
    const cont = (a, b) => a[4] === b[4] && Math.abs(a[6] - b[5]) < 1e-9 && (a[6] - a[5]) * (b[6] - b[5]) > 0;
    for (let i = 0; i < kept.length; i++) {
      if (used[i]) continue;
      const loop = [], startK = key(kept[i][0], kept[i][1]);
      let cur = i, g = 0;
      while (cur >= 0 && g++ < kept.length + 2) {
        used[cur] = 1; loop.push(kept[cur]);
        const pc = kept[cur], ek = key(pc[2], pc[3]);
        if (ek === startK) break;
        const l = from.get(ek);
        let next = -1;
        if (l) { for (const c of l) if (!used[c] && cont(pc, kept[c])) { next = c; break; } if (next < 0) for (const c of l) if (!used[c]) { next = c; break; } }
        if (next < 0) {                               /* a gap from rounding: the nearest free start within a hair */
          let best = 1e-3;
          for (let c = 0; c < kept.length; c++) if (!used[c]) { const dd = Math.hypot(kept[c][0] - pc[2], kept[c][1] - pc[3]); if (dd < best) { best = dd; next = c; } }
        }
        cur = next;
      }
      if (loop.length > 1) loops.push(loop);
    }
    /* write the loops as the original curves between the crossings */
    let d = '';
    const f = (v) => { v = Math.round(v * 1000) / 1000; return Object.is(v, -0) ? '0' : String(v); };
    for (const loop of loops) {
      let st = 0;
      for (let k = 0; k < loop.length; k++) { if (!cont(loop[(k + loop.length - 1) % loop.length], loop[k])) { st = k; break; } }
      const L2 = loop.slice(st).concat(loop.slice(0, st));
      d += 'M' + f(L2[0][0]) + ' ' + f(L2[0][1]);
      for (let k = 0; k < L2.length;) {
        let e = k;
        while (e + 1 < L2.length && cont(L2[e], L2[e + 1])) e++;
        const a = L2[k], b = L2[e], c = curves[a[4]];
        if (c.length === 4) d += 'L' + f(b[2]) + ' ' + f(b[3]);
        else {
          const t0 = a[5], t1 = b[6];
          const sxx = blossom(c[0], c[2], c[4], c[6], t0, t0, t0), syy = blossom(c[1], c[3], c[5], c[7], t0, t0, t0);
          const exx = blossom(c[0], c[2], c[4], c[6], t1, t1, t1), eyy = blossom(c[1], c[3], c[5], c[7], t1, t1, t1);
          d += 'C' + f(blossom(c[0], c[2], c[4], c[6], t0, t0, t1) + a[0] - sxx) + ' ' + f(blossom(c[1], c[3], c[5], c[7], t0, t0, t1) + a[1] - syy) + ' ' +
            f(blossom(c[0], c[2], c[4], c[6], t0, t1, t1) + b[2] - exx) + ' ' + f(blossom(c[1], c[3], c[5], c[7], t0, t1, t1) + b[3] - eyy) + ' ' + f(b[2]) + ' ' + f(b[3]);
        }
        k = e + 1;
      }
      d += 'Z';
    }
    return {d, n: loops.length};
  }
  /* the shape of a boolean group in its own space: {k: R_PATH, p, rule, d} (kept until something inside it changes) */
  function boolGeom(n, id, v, rec) {
    const holder = v !== null && v !== undefined ? v : (rec || (id !== undefined && id !== null ? derive(id, n) : null));
    const stamp = v !== null && v !== undefined ? 'v' : holder ? holder.cv + ':' + resEpoch + ':' + compEpoch + ':' + n.bool : '';
    if (holder && holder.bg && holder.bgk === stamp) return holder.bg;
    const W0 = {curves: []}, kids = boolKids(id, v), ops = [];
    const I = [1, 0, 0, 1, 0, 0];
    for (const k of kids) { const o = operandOf(k.n, k.id, k.v, I, 1, W0); if (o) ops.push(o); else if (n.bool === 'subtract' && !ops.length && k.n.visible !== false) break; }
    let res = null;
    if (ops.length) { try { res = boolCompute(ops.length === 1 ? ops[0] : {op: n.bool, kids: ops}, W0.curves); } catch (e) { res = null; if (window.console) console.error('[HD.render] boolean', e); } }
    let g;
    if (!res || !res.d) g = {k: R_PATH, r: null, p: new Path2D(), rule: 'nonzero', open: false, inv: null, d: '', ok: !!res};
    else { let p; try { p = new Path2D(res.d); } catch (e) { p = new Path2D(); } g = {k: R_PATH, r: null, p, rule: 'nonzero', open: false, inv: null, d: res.d, ok: true}; }
    if (holder) { holder.bg = g; holder.bgk = stamp; }
    return g;
  }

  /* ------------------------------------------------------------------ images */
  const imgs = new Map();                  /* hash -> {st, img, at} */
  function assetURL(hash) { return typeof api.assetURL === 'function' ? api.assetURL(hash) : '/api/design/assets/' + encodeURIComponent(hash); }
  function image(hash) {
    if (typeof hash !== 'string' || !/^[A-Za-z0-9_.-]{4,160}$/.test(hash)) return null;
    let e = imgs.get(hash);
    if (e) {
      if (e.st === 'ok') return e.img;
      if (e.st === 'load' || now() - e.at < 30000) return null;
    }
    e = {st: 'load', img: null, at: now()};
    imgs.set(hash, e);
    let token = '';
    try { token = localStorage.getItem('hoola.console.token') || ''; } catch (err) { token = ''; }
    const fail = () => { e.st = 'err'; e.at = now(); };
    let p;
    try { p = fetch(assetURL(hash), token ? {headers: {Authorization: 'Bearer ' + token}} : undefined); } catch (err) { fail(); return null; }
    p.then(r => { if (!r.ok) throw new Error('asset ' + r.status); return r.blob(); }).then(blob => new Promise((res, rej) => {
      const im = new Image();
      im.onload = () => res(im);
      im.onerror = () => rej(new Error('not an image'));
      im.src = URL.createObjectURL(blob);
    })).then(im => { e.img = im; e.st = 'ok'; imgEpoch++; sceneFull = true; schedule(); }).catch(fail);
    return null;
  }

  /* ------------------------------------------------------------------ fonts */
  const SYSTEM_FONTS = {'serif': 1, 'sans-serif': 1, 'monospace': 1, 'system-ui': 1, 'cursive': 1, 'fantasy': 1, 'arial': 1, 'helvetica': 1,
    'times new roman': 1, 'times': 1, 'georgia': 1, 'courier new': 1, 'courier': 1, 'verdana': 1, 'tahoma': 1, 'trebuchet ms': 1, 'segoe ui': 1};
  const fam = new Map();                   /* family -> {st: 'new'|'css'|'ok'|'err', specs:Set, link} */
  let fontTimer = 0;
  const fontsDone = new Set();
  function famReady(name) {
    const k = String(name || '').trim();
    if (!k || SYSTEM_FONTS[k.toLowerCase()]) return true;
    const f = fam.get(k);
    return !!f && (f.st === 'ok' || f.st === 'err');
  }
  function fontSpec(st) { return (st.italic ? 'italic ' : '') + st.weight + ' 16px "' + st.font.replace(/["\\]/g, '') + '"'; }
  function fontArrived(family) {
    fontsDone.add(family);
    if (fontTimer) return;
    fontTimer = setTimeout(() => {
      fontTimer = 0;
      const list = Array.from(fontsDone);
      fontsDone.clear();
      L.fontsChanged();
      resEpoch++; sceneFull = true;
      for (const f of list) { try { L.reflow(f); } catch (e) { /* view only */ } }
      schedule();
    }, 30);
  }
  function loadSpec(f, family, spec) {
    if (!document.fonts || !document.fonts.load) { f.st = 'ok'; fontArrived(family); return; }
    document.fonts.load(spec).then((faces) => { if (f.st !== 'ok') f.st = 'ok'; if (faces && faces.length) fontArrived(family); else fontArrived(family); }, () => { if (f.st !== 'ok') f.st = 'err'; });
  }
  function needFont(st) {
    const family = String(st.font || '').trim();
    if (!family || SYSTEM_FONTS[family.toLowerCase()]) return;
    let f = fam.get(family);
    const spec = fontSpec(st);
    if (f) {
      if (f.specs.has(spec)) return;
      f.specs.add(spec);
      if (f.st === 'ok' || f.st === 'css') loadSpec(f, family, spec);
      return;
    }
    f = {st: 'new', specs: new Set([spec]), link: null};
    fam.set(family, f);
    let have = false;
    try { if (document.fonts) document.fonts.forEach(ff => { if (String(ff.family).replace(/["']/g, '').trim() === family) have = true; }); } catch (e) { have = false; }
    if (have) { f.st = 'css'; loadSpec(f, family, spec); return; }
    if (!/^[A-Za-z0-9 ]+$/.test(family) || api.webFonts === false) { f.st = 'err'; return; }
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://fonts.googleapis.com/css?family=' + encodeURIComponent(family).replace(/%20/g, '+') +
      ':100,200,300,400,500,600,700,800,900,100italic,200italic,300italic,400italic,500italic,600italic,700italic,800italic,900italic&display=swap';
    link.setAttribute('data-hd-font', family);
    link.onload = () => { f.st = 'css'; for (const sp of f.specs) loadSpec(f, family, sp); };
    link.onerror = () => { f.st = 'err'; };
    f.link = link;
    (document.head || document.documentElement).appendChild(link);
  }
  L.fontHook = {ready: (st) => famReady(st.font), need: needFont};
  /* loadFont(family, weight?, italic?) -> Promise: wait for a font BEFORE setting it on a text (no reflow later) */
  function loadFont(family, weight, italic) {
    const st = {font: String(family || ''), weight: weight || 400, italic: !!italic};
    needFont(st);
    return new Promise((res) => {
      const t0 = now();
      (function poll() { if (famReady(st.font) || now() - t0 > 8000) res(famReady(st.font)); else setTimeout(poll, 60); })();
    });
  }
  function fontLoaded(family) { const f = fam.get(family); if (f) f.st = 'ok'; else fam.set(family, {st: 'ok', specs: new Set(), link: null}); fontArrived(family); }

  /* ------------------------------------------------------------------ derived records (extent, cost, versions) */
  const D = new Map();
  function newRec(par) {
    return {cv: 0, v: -1, re: 0, ce: 0, x0: 0, y0: 0, x1: 0, y1: 0, n: 1, cost: 1, flags: 0, par, hot: 0,
      wx0: 0, wy0: 0, wx1: 0, wy1: 0, serial: 0, tl: null, vt: null, vtk: '', bg: null, bgk: ''};
  }
  function recOf(id, n) {
    let r = D.get(id);
    if (r === undefined) { r = newRec(n ? n.parent : undefined); D.set(id, r); }
    return r;
  }
  function clips(n) { return n.type !== 'GROUP' && n.type !== 'SECTION' && n.type !== 'PAGE' && !!G(n, 'clip'); }
  function fxList(n) {
    if (n.effects === undefined && n.effectStyle === undefined) return null;
    const a = L.effects(n);
    if (!a.length) return null;
    let out = null;
    for (let i = 0; i < a.length; i++) { const e = a[i]; if (e && e.visible !== false && e.type) (out || (out = [])).push(e); }
    return out;
  }
  function fxGrow(fx, box) {
    let l = 0, t = 0, r = 0, b = 0;
    for (let i = 0; i < fx.length; i++) {
      const e = fx[i], bl = Math.max(0, num(+e.blur, 0));
      if (e.type === 'drop') {
        const sp = Math.max(0, num(+e.spread, 0)), k = bl * 1.5 + sp + 1, x = num(+e.x, 0), y = num(+e.y, 0);
        l = Math.max(l, k - x); r = Math.max(r, k + x); t = Math.max(t, k - y); b = Math.max(b, k + y);
      } else if (e.type === 'blur') { const k = bl * 1.5 + 1; l = Math.max(l, k); r = Math.max(r, k); t = Math.max(t, k); b = Math.max(b, k); }
    }
    box[0] -= l; box[1] -= t; box[2] += r; box[3] += b;
  }
  function derive(id, n) {
    let r = D.get(id);
    if (r === undefined) { r = newRec(n.parent); D.set(id, r); }
    if (r.v === r.cv && r.re === resEpoch && ((r.flags & F_INST) === 0 || r.ce === compEpoch)) return r;
    const type = n.type, w = W(n), h = H(n), page = type === 'PAGE';
    let x0 = page ? Infinity : 0, y0 = page ? Infinity : 0, x1 = page ? -Infinity : w, y1 = page ? -Infinity : h, flags = 0, cnt = 1, cost = 1;
    r.tl = null;
    const sp = L.paints(n, 'strokes');
    if (sp.length && anyVis(sp)) {
      const sw = Math.max(0, num(+G(n, 'strokeWeight'), 1)), al = G(n, 'strokeAlign');
      let so = al === 'outside' ? sw : al === 'inside' ? 0 : sw / 2;
      if (type === 'LINE') so = sw;
      else if (type === 'VECTOR' || type === 'POLYGON' || type === 'STAR' || type === 'TEXT' || (type === 'GROUP' && n.bool !== undefined)) so = sw * 2 + 1;
      x0 -= so; y0 -= so; x1 += so; y1 += so; cost++;
    }
    const fp = L.paints(n, 'fills');
    for (let i = 0; i < fp.length; i++) { const p = fp[i]; if (p && p.type === 'image') { flags |= F_IMG; cost += 2; } else if (p && p.type !== 'solid') cost++; }
    if (type === 'TEXT') {
      const tl = L.textLayout(n);
      r.tl = tl; flags |= F_TEXT; cost += 2 + (tl.lines.length >> 2);
      const slop = num(+G(n, 'fontSize'), 16) * 0.35;
      for (let i = 0; i < tl.lines.length; i++) {
        const ln = tl.lines[i];
        x0 = Math.min(x0, ln.x - slop); x1 = Math.max(x1, ln.x + ln.w + slop); y0 = Math.min(y0, ln.y - slop * 0.5); y1 = Math.max(y1, ln.y + ln.h + slop * 0.5);
      }
    } else if (type === 'INSTANCE') {
      flags |= F_INST; instSeen = true;
      r.ce = compEpoch; r.v = r.cv; r.re = resEpoch;       /* so instTree sees a settled record */
      const vt = instTree(id, n, r);
      cnt += vt.count; cost += vt.count * 1.5; flags |= vt.flags;
      if (!clips(vt.n)) { const e = vExt(vt); x0 = Math.min(x0, e[0]); y0 = Math.min(y0, e[1]); x1 = Math.max(x1, e[2]); y1 = Math.max(y1, e[3]); }
    } else if (CONT[type] === 1) {
      const ks = S().children(id), clip = clips(n);
      for (let i = 0; i < ks.length; i++) {
        const cn = S().get(ks[i]);
        if (!cn) continue;
        const cr = derive(ks[i], cn);
        cnt += cr.n; cost += cr.cost; flags |= cr.flags & F_UP;
        if (cn.mask === true) flags |= F_MASKKID;
        if (blends(cn)) flags |= F_BLENDKID;        /* it mixes with what lies under this frame: the frame can not live in a bitmap */
        if (!clip && cn.visible !== false) {
          if (!cn.rot && cn.flipH !== true && cn.flipV !== true) {
            const cx = num(cn.x, 0), cy = num(cn.y, 0);
            if (cr.x0 + cx < x0) x0 = cr.x0 + cx; if (cr.y0 + cy < y0) y0 = cr.y0 + cy; if (cr.x1 + cx > x1) x1 = cr.x1 + cx; if (cr.y1 + cy > y1) y1 = cr.y1 + cy;
          } else {
            localMat(cn, LM);
            boxUnder(LM[0], LM[1], LM[2], LM[3], LM[4], LM[5], cr.x0, cr.y0, cr.x1, cr.y1);
            if (BX[0] < x0) x0 = BX[0]; if (BX[1] < y0) y0 = BX[1]; if (BX[2] > x1) x1 = BX[2]; if (BX[3] > y1) y1 = BX[3];
          }
        }
      }
    }
    const fx = fxList(n);
    if (fx) {
      const box = [x0, y0, x1, y1];
      fxGrow(fx, box);
      x0 = box[0]; y0 = box[1]; x1 = box[2]; y1 = box[3];
      flags |= F_FX;
      for (let i = 0; i < fx.length; i++) { if (fx[i].type === 'bgblur') flags |= F_BG; cost += fx[i].type === 'blur' ? 24 : 14; }
    }
    if (x0 === Infinity) { x0 = 0; y0 = 0; x1 = 0; y1 = 0; }
    r.x0 = x0; r.y0 = y0; r.x1 = x1; r.y1 = y1; r.n = cnt; r.cost = cost; r.flags = flags;
    r.v = r.cv; r.re = resEpoch; r.ce = compEpoch;
    return r;
  }

  /* ------------------------------------------------------------------ instances: the component drawn with overrides, no node copies */
  const EMPTY = Object.freeze([]);
  function instRoot(inst, ovs, depth, key, seen) {
    const s = S(), comp = inst.comp ? s.get(inst.comp) : null;
    if (!comp || depth > 6 || seen.has(inst.comp)) return {n: inst, id: inst.comp || '', key, kids: EMPTY, sx: 1, sy: 1, count: 1, flags: 0, ext: null};
    const rootN = Object.assign({}, comp, inst);
    rootN.type = 'INSTANCE';
    if (inst.w === undefined) rootN.w = comp.w;
    if (inst.h === undefined) rootN.h = comp.h;
    const all = [{ov: inst.ov && typeof inst.ov === 'object' ? inst.ov : {}, path: ''}].concat(ovs);
    for (const e of all) { const o = e.path === '' ? e.ov[''] : undefined; if (o && typeof o === 'object') Object.assign(rootN, o); }
    const seen2 = new Set(seen);
    seen2.add(inst.comp);
    const v = {n: rootN, id: inst.comp, key, kids: [], sx: 1, sy: 1, count: 1, flags: 0, ext: null, inst: true, cw: 0, ch: 0};
    const cw = W(comp), ch = H(comp);
    v.cw = cw; v.ch = ch;
    v.sx = cw > EPS ? W(rootN) / cw : 1; v.sy = ch > EPS ? H(rootN) / ch : 1;
    const ks = s.children(inst.comp);
    for (let i = 0; i < ks.length; i++) { const k = vNode(ks[i], all, depth, key, seen2); if (k) { v.kids.push(k); v.count += k.count; v.flags |= k.flags; } }
    return v;
  }
  function vNode(cid, ovs, depth, keyPrefix, seen) {
    const s = S(), c = s.get(cid);
    if (!c) return null;
    const ovs2 = [];
    let n = c;
    for (let i = 0; i < ovs.length; i++) {
      const e = ovs[i], path = e.path ? e.path + '/' + cid : cid, o = e.ov[path];
      ovs2.push({ov: e.ov, path});
      if (o && typeof o === 'object') { if (n === c) n = Object.assign({}, c); Object.assign(n, o); }
    }
    const key = keyPrefix + '/' + cid;
    let v;
    if (n.type === 'INSTANCE') v = instRoot(n, ovs2, depth + 1, key, seen);
    else {
      v = {n, id: cid, key, kids: EMPTY, sx: 1, sy: 1, count: 1, flags: 0, ext: null};
      if (CONT[n.type] === 1) {
        const ks = s.children(cid);
        if (ks.length) { v.kids = []; for (let i = 0; i < ks.length; i++) { const k = vNode(ks[i], ovs2, depth, key, seen); if (k) { v.kids.push(k); v.count += k.count; v.flags |= k.flags; } } }
      }
    }
    const f = L.paints(n, 'fills');
    for (let i = 0; i < f.length; i++) if (f[i] && f[i].type === 'image') v.flags |= F_IMG;
    if (n.type === 'TEXT') v.flags |= F_TEXT;
    if (blends(n)) v.flags |= F_BLENDKID;
    const fx = fxList(n);
    if (fx) for (let i = 0; i < fx.length; i++) if (fx[i].type === 'bgblur') v.flags |= F_BG;
    return v;
  }
  function instTree(id, n, r) {
    const key = r.cv + ':' + compEpoch + ':' + resEpoch;
    if (r.vt !== null && r.vtk === key) return r.vt;
    r.vt = instRoot(n, [], 0, id, new Set());
    r.vtk = key;
    fitInst(r.vt, 0);
    return r.vt;
  }
  /* An instance at another size than its component. When the component has auto layout, or its children carry
     constraints, the children are laid out again for the new size (HD.layout.virtual, the same code that lays out real
     frames); only a component with neither is simply scaled, as before. Top down, so an instance inside it that got a
     new size from that layout is fitted in its turn. */
  function fitInst(v, depth) {
    if (v.inst === true && depth < 8) {
      v.sx = v.cw > EPS ? W(v.n) / v.cw : 1; v.sy = v.ch > EPS ? H(v.n) / v.ch : 1;
      if ((Math.abs(v.sx - 1) > 1e-6 || Math.abs(v.sy - 1) > 1e-6) && v.kids.length && typeof L.virtual === 'function') {
        const l = v.n.layout;
        let wants = !!(l && (l.mode === 'h' || l.mode === 'v'));
        for (let i = 0; i < v.kids.length && !wants; i++) { const c = v.kids[i].n.cons; if (c !== undefined && c !== null) wants = true; }
        if (wants && L.virtual(v, v.cw, v.ch)) { v.sx = 1; v.sy = 1; }
      }
    }
    for (let i = 0; i < v.kids.length; i++) fitInst(v.kids[i], v.kids[i].inst === true ? depth + 1 : depth);
  }
  /* extent of a virtual node in its own space (kept on the tree, which is rebuilt whenever anything it shows changes) */
  function vExt(v) {
    if (v.ext) return v.ext;
    const n = v.n, w = W(n), h = H(n);
    const box = [0, 0, w, h];
    const sp = L.paints(n, 'strokes');
    if (sp.length && anyVis(sp)) { const so = Math.max(0, num(+G(n, 'strokeWeight'), 1)) * 2 + 1; box[0] -= so; box[1] -= so; box[2] += so; box[3] += so; }
    if (n.type === 'TEXT') { const sl = num(+G(n, 'fontSize'), 16) * 0.4, tl = L.textLayout(n); box[0] -= sl; box[1] -= sl; box[2] = Math.max(box[2], tl.cw) + sl; box[3] = Math.max(box[3], tl.ch) + sl; }
    if (v.kids.length && !clips(n)) {
      const m = [1, 0, 0, 1, 0, 0];
      for (let i = 0; i < v.kids.length; i++) {
        const k = v.kids[i];
        if (k.n.visible === false) continue;
        const e = vExt(k);
        localMat(k.n, m);
        boxUnder(m[0] * v.sx, m[1] * v.sy, m[2] * v.sx, m[3] * v.sy, m[4] * v.sx, m[5] * v.sy, e[0], e[1], e[2], e[3]);
        if (BX[0] < box[0]) box[0] = BX[0]; if (BX[1] < box[1]) box[1] = BX[1]; if (BX[2] > box[2]) box[2] = BX[2]; if (BX[3] > box[3]) box[3] = BX[3];
      }
    }
    const fx = fxList(n);
    if (fx) fxGrow(fx, box);
    v.ext = box;
    return box;
  }

  /* ------------------------------------------------------------------ scratch layers (group opacity, blend, effects, masks) */
  const pool = [];
  let LD = 0;
  function getLayer(w, h) {
    const i = LD++;
    let l = pool[i];
    if (!l) { const cv = document.createElement('canvas'); cv.width = Math.max(64, w); cv.height = Math.max(64, h); l = pool[i] = {cv, ctx: cv.getContext('2d')}; }
    else if (l.cv.width < w || l.cv.height < h) { l.cv.width = Math.max(l.cv.width, w); l.cv.height = Math.max(l.cv.height, h); }
    const c = l.ctx;
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.globalAlpha = 1; c.globalCompositeOperation = 'source-over';
    if (HAS_FILTER) c.filter = 'none';
    c.shadowColor = 'rgba(0,0,0,0)'; c.shadowBlur = 0; c.shadowOffsetX = 0; c.shadowOffsetY = 0;
    c.clearRect(0, 0, w, h);
    return l;
  }
  function trimPool() {
    const lim = Math.max(1, (scene ? scene.width * scene.height : 1e6)) * 3;
    for (let i = 0; i < pool.length; i++) { const cv = pool[i].cv; if (cv.width * cv.height > lim) { cv.width = 64; cv.height = 64; } }
  }
  function subT(T, ctx, lx0, ly0, LW, LH) {
    return {ctx, clips: [0, 0, LW, LH], bounds: [0, 0, LW, LH], lod: T.lod, cache: T.cache, canBuild: T.canBuild, record: T.record, exact: T.exact,
      bs: T.bs, btx: T.btx - lx0, bty: T.bty - ly0, serial: T.serial, budgetEnd: T.budgetEnd, now: T.now, root: T.root || T, inexact: false, backdrop: false};
  }

  /* ------------------------------------------------------------------ bitmap cache */
  const C = new Map();
  let cacheBytes = 0;
  let CACHE_CAP = 256 * 1024 * 1024;           /* bytes of bitmap pixels kept at most (least recently used go first) */
  const CACHE_MAXD = 4096, CACHE_MAXA = 6e6, COST_MIN = 14, HOT_MS = 260;
  function dropEntry(id, en) { cacheBytes -= en.bytes; en.cv.width = 0; en.cv.height = 0; C.delete(id); }
  function clearCache() { for (const [id, en] of C) { en.cv.width = 0; en.cv.height = 0; C.delete(id); } cacheBytes = 0; }
  function evict() {
    if (cacheBytes <= CACHE_CAP) return;
    const arr = Array.from(C.entries()).sort((a, b) => a[1].used - b[1].used);
    for (let i = 0; i < arr.length && cacheBytes > CACHE_CAP * 0.75; i++) dropEntry(arr[i][0], arr[i][1]);
  }
  function frac0(t) { return Math.abs(t - Math.round(t)) < 0.01; }
  function blitExact(T, en, op, blendOp, me, mf) {
    const ctx = T.ctx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = op;
    if (blendOp !== 'source-over') ctx.globalCompositeOperation = blendOp;
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(en.cv, Math.round(me - en.offX), Math.round(mf - en.offY));
    ctx.imageSmoothingEnabled = true;
    ctx.globalAlpha = 1;
    if (blendOp !== 'source-over') ctx.globalCompositeOperation = 'source-over';
    en.used = T.serial; stats.blits++;
  }
  function blitScaled(T, en, op, blendOp, ma, mb, mc, md, me, mf) {
    const ctx = T.ctx;
    ctx.setTransform(ma, mb, mc, md, me, mf);
    ctx.globalAlpha = op;
    if (blendOp !== 'source-over') ctx.globalCompositeOperation = blendOp;
    ctx.drawImage(en.cv, -en.offX / en.sc, -en.offY / en.sc, en.bw / en.sc, en.bh / en.sc);
    ctx.globalAlpha = 1;
    if (blendOp !== 'source-over') ctx.globalCompositeOperation = 'source-over';
    en.used = T.serial; stats.blits++;
    (T.root || T).inexact = true;
  }
  /* true = the node was drawn from its bitmap. A bitmap is shown only while its content version still matches;
     1:1 when it was made for exactly this scale and pixel phase, scaled (and marked for a settle repaint) otherwise. */
  function tryCache(T, n, id, rec, type, w, h, op, blendOp, ma, mb, mc, md, me, mf, dx0, dy0, dx1, dy1) {
    const axis = mb === 0 && mc === 0 && ma > 0 && md > 0 && Math.abs(ma - md) < 1e-9 * (ma + md);
    let en = C.get(id);
    if (en !== undefined && (en.cvn !== rec.cv || en.re !== resEpoch || ((rec.flags & F_INST) !== 0 && en.ce !== compEpoch) || ((rec.flags & F_IMG) !== 0 && en.ie !== imgEpoch))) { dropEntry(id, en); en = undefined; }
    if (en !== undefined) {
      if (axis && en.axis && Math.abs(en.sc - ma) <= 1e-7 * ma && frac0(me - en.offX) && frac0(mf - en.offY)) { blitExact(T, en, op, blendOp, me, mf); return true; }
      if (!T.exact) { blitScaled(T, en, op, blendOp, ma, mb, mc, md, me, mf); return true; }
      dropEntry(id, en);
    }
    /* a bitmap is only ever MADE for an upright node at the scale and pixel phase it has right now (so it can be shown 1:1) */
    if (!axis || !T.canBuild || rec.hot > T.now || now() > T.budgetEnd) return false;
    const px0 = Math.floor(dx0), py0 = Math.floor(dy0);
    const bw = Math.ceil(dx1) - px0, bh = Math.ceil(dy1) - py0, sc = ma, offX = me - px0, offY = mf - py0;
    if (bw < 1 || bh < 1 || bw > CACHE_MAXD || bh > CACHE_MAXD || bw * bh > CACHE_MAXA) return false;
    const cv = document.createElement('canvas');
    cv.width = bw; cv.height = bh;
    const T2 = {ctx: cv.getContext('2d'), clips: null, bounds: [0, 0, bw, bh], lod: T.lod, cache: false, canBuild: false, record: false, exact: true,
      bs: sc, btx: 0, bty: 0, serial: T.serial, budgetEnd: 0, now: T.now, root: null, inexact: false, backdrop: false};
    const saveLD = LD;
    try { paintBody(T2, n, id, null, rec, type, w, h, 1, 'source-over', sc, 0, 0, sc, offX, offY, 0, 0, bw, bh); } finally { LD = saveLD; }
    en = {cv, sc, axis, offX, offY, bw, bh, cvn: rec.cv, ce: compEpoch, ie: imgEpoch, re: resEpoch, used: T.serial, bytes: bw * bh * 4};
    C.set(id, en);
    cacheBytes += en.bytes;
    stats.built++;
    blitExact(T, en, op, blendOp, me, mf);
    if (cacheBytes > CACHE_CAP) evict();
    return true;
  }

  /* ------------------------------------------------------------------ painting */
  function paintKidsFrom(T, id, v, start, a, b, c, d, e, f, end) {
    if (v !== null) {
      const ks = v.kids, lim = end === undefined ? ks.length : end;
      for (let i = start; i < lim; i++) {
        const k = ks[i];
        if (k.n.mask === true && k.n.visible !== false) { i = paintMasked(T, id, v, i, k.n, k.key, k, a, b, c, d, e, f, lim) - 1; continue; }
        paintNode(T, k.n, k.key, k, a, b, c, d, e, f);
      }
      return;
    }
    const s = S(), ks = s.children(id), lim = end === undefined ? ks.length : end;
    for (let i = start; i < lim; i++) {
      const cn = s.get(ks[i]);
      if (cn === undefined) continue;
      if (cn.mask === true && cn.visible !== false) { i = paintMasked(T, id, null, i, cn, ks[i], null, a, b, c, d, e, f, lim) - 1; continue; }
      paintNode(T, cn, ks[i], null, a, b, c, d, e, f);
    }
  }
  /* can this mask be a plain clip? Only a simple outline that is fully opaque inside (or has no paint at all: then its
     outline is taken); anything else masks by the ALPHA of its own picture: a see-through fill shows less, a stroke
     alone shows a ring, a gradient to transparent fades what is under it */
  function clipMask(mn) {
    if (GEO_MASK[mn.type] !== 1 || mn.effects !== undefined || mn.effectStyle !== undefined || (mn.opacity !== undefined && mn.opacity < 0.999) || mn.bind !== undefined) return false;
    const f = L.paints(mn, 'fills'), st = L.paints(mn, 'strokes');
    const strokes = anyVis(st) && num(+G(mn, 'strokeWeight'), 1) > 0;
    if (!anyVis(f)) return !strokes;
    if (strokes && G(mn, 'strokeAlign') !== 'inside') return false;
    for (let i = 0; i < f.length; i++) { const p = f[i]; if (vis(p) && (p.type === 'solid' || p.type === undefined) && (p.opacity === undefined || p.opacity >= 0.999) && rgba(p.color, 1).charCodeAt(0) === 35) return true; }
    return false;
  }
  /* a mask shows the siblings above it (up to the next mask) only where it is; its own picture is not drawn.
     Returns the index of the sibling the caller goes on with. */
  function paintMasked(T, pid, pv, i, mn, mid, mv, a, b, c, d, e, f, lim) {
    const ctx = T.ctx, w = W(mn), h = H(mn), s = S();
    const list = pv !== null ? pv.kids : s.children(pid);
    let j = i + 1;
    for (; j < lim; j++) { const kn = pv !== null ? list[j].n : s.get(list[j]); if (kn && kn.mask === true && kn.visible !== false) break; }
    if (j === i + 1) return j;
    localMat(mn, LM);
    const ma = a * LM[0] + c * LM[1], mb = b * LM[0] + d * LM[1], mc = a * LM[2] + c * LM[3], md = b * LM[2] + d * LM[3], me = a * LM[4] + c * LM[5] + e, mf = b * LM[4] + d * LM[5] + f;
    if (clipMask(mn)) {
      ctx.save();
      ctx.setTransform(ma, mb, mc, md, me, mf);
      clipGeom(ctx, geomOf(mn, mn.type, w, h), w, h);
      paintKidsFrom(T, pid, pv, i + 1, a, b, c, d, e, f, j);
      ctx.restore();
      return j;
    }
    let x0 = 0, y0 = 0, x1 = w, y1 = h;
    if (mv === null) { const r = derive(mid, mn); x0 = r.x0; y0 = r.y0; x1 = r.x1; y1 = r.y1; } else { const ex = vExt(mv); x0 = ex[0]; y0 = ex[1]; x1 = ex[2]; y1 = ex[3]; }
    boxUnder(ma, mb, mc, md, me, mf, x0, y0, x1, y1);
    const B = T.bounds;
    const lx0 = Math.max(Math.floor(BX[0]) - 1, B[0]), ly0 = Math.max(Math.floor(BX[1]) - 1, B[1]), lx1 = Math.min(Math.ceil(BX[2]) + 1, B[2]), ly1 = Math.min(Math.ceil(BX[3]) + 1, B[3]);
    const LW = lx1 - lx0, LH = ly1 - ly0;
    if (LW <= 0 || LH <= 0 || LW * LH > 5e7) return j;
    const saveLD = LD;
    try {
      const A = getLayer(LW, LH), Bm = getLayer(LW, LH);
      stats.layers += 2;
      paintKidsFrom(subT(T, A.ctx, lx0, ly0, LW, LH), pid, pv, i + 1, a, b, c, d, e - lx0, f - ly0, j);
      const mask2 = mn.blend === undefined ? mn : Object.assign({}, mn, {blend: 'normal'});
      paintNode(subT(T, Bm.ctx, lx0, ly0, LW, LH), mask2, mid, mv, a, b, c, d, e - lx0, f - ly0);
      A.ctx.setTransform(1, 0, 0, 1, 0, 0);
      A.ctx.globalAlpha = 1; A.ctx.globalCompositeOperation = 'destination-in';
      A.ctx.drawImage(Bm.cv, 0, 0, LW, LH, 0, 0, LW, LH);
      A.ctx.globalCompositeOperation = 'source-over';
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalAlpha = 1;
      ctx.drawImage(A.cv, 0, 0, LW, LH, lx0, ly0, LW, LH);
    } finally { LD = saveLD; }
    return j;
  }

  function paintNode(T, n, id, v, a, b, c, d, e, f) {
    if (n === undefined || n === null || n.visible === false) return;
    if (n.bind !== undefined && G(n, 'visible') === false) return;
    const type = n.type === 'GROUP' ? dtype(n) : n.type;
    if (type === 'TEXT' && id === editingId) return;
    const w = W(n), h = type === 'LINE' ? 0 : num(n.h, 100);
    let ma, mb, mc, md, me, mf;
    if (!n.rot && n.flipH !== true && n.flipV !== true) {
      const x = num(n.x, 0), y = num(n.y, 0);
      ma = a; mb = b; mc = c; md = d; me = a * x + c * y + e; mf = b * x + d * y + f;
    } else {
      localMat(n, LM);
      ma = a * LM[0] + c * LM[1]; mb = b * LM[0] + d * LM[1]; mc = a * LM[2] + c * LM[3]; md = b * LM[2] + d * LM[3];
      me = a * LM[4] + c * LM[5] + e; mf = b * LM[4] + d * LM[5] + f;
    }
    let rec = null;
    if (v === null) {
      rec = derive(id, n);
      boxUnder(ma, mb, mc, md, me, mf, rec.x0, rec.y0, rec.x1, rec.y1);
    } else {
      const ex = vExt(v);
      boxUnder(ma, mb, mc, md, me, mf, ex[0], ex[1], ex[2], ex[3]);
    }
    const dx0 = BX[0], dy0 = BX[1], dx1 = BX[2], dy1 = BX[3];
    const cl = T.clips;
    if (cl !== null) {
      let hit = false;
      for (let i = 0; i < cl.length; i += 4) if (dx1 > cl[i] && dx0 < cl[i + 2] && dy1 > cl[i + 1] && dy0 < cl[i + 3]) { hit = true; break; }
      if (!hit) { stats.culled++; return; }
    }
    if (rec !== null && T.record) {
      const bs = T.bs;
      rec.wx0 = (dx0 - T.btx) / bs; rec.wy0 = (dy0 - T.bty) / bs; rec.wx1 = (dx1 - T.btx) / bs; rec.wy1 = (dy1 - T.bty) / bs; rec.serial = T.serial;
    }
    let op = n.opacity;
    if (n.bind !== undefined) op = G(n, 'opacity');
    if (op === undefined) op = 1; else { op = num(+op, 1); if (op > 1) op = 1; }
    if (op <= 0.003) return;
    if (T.lod) {
      const dw = dx1 - dx0, dh = dy1 - dy0;
      if (dw < 0.35 && dh < 0.35) return;
      if (dw < 2.6 && dh < 2.6) {
        const col = flatColor(n, 0);
        stats.flat++;
        if (col !== null) {
          const ctx = T.ctx;
          ctx.setTransform(1, 0, 0, 1, 0, 0);
          ctx.globalAlpha = op * Math.min(1, Math.max(0.25, Math.max(dw, dh) / 2.6));
          ctx.fillStyle = col;
          ctx.fillRect(dx0, dy0, dw < 1 ? 1 : dw, dh < 1 ? 1 : dh);
          ctx.globalAlpha = 1;
        }
        return;
      }
    }
    const bl = n.blend;
    const blendOp = bl === undefined || bl === 'normal' ? 'source-over' : (BLEND[bl] || 'source-over');
    if (T.lod && dx1 - dx0 < 5.5 && dy1 - dy0 < 5.5 && blendOp === 'source-over' && n.effects === undefined && (type === 'RECT' || type === 'ELLIPSE' || ((type === 'POLYGON' || type === 'STAR' || type === 'VECTOR') && dx1 - dx0 < 4 && dy1 - dy0 < 4))) {
      /* a few pixels big: its colour in its place is all the eye can tell */
      const f = L.paints(n, 'fills');
      let col = null;
      for (let i = f.length - 1; i >= 0; i--) { const p = f[i]; if (!vis(p)) continue; col = p.type === 'solid' || p.type === undefined ? rgba(p.color, p.opacity) : p.type === 'image' ? '#C9C9CF' : (p.stops && p.stops[0] ? rgba(p.stops[0].color, p.opacity) : null); break; }
      if (col !== null) {
        const ctx = T.ctx;
        stats.flat++;
        ctx.globalAlpha = op; ctx.fillStyle = col;
        if (mb === 0 && mc === 0 && type !== 'ELLIPSE') { ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillRect(me, mf, ma * w, md * h); }
        else { ctx.setTransform(ma, mb, mc, md, me, mf); if (type === 'ELLIPSE') { ctx.beginPath(); ctx.ellipse(w / 2, h / 2, w / 2, h / 2, 0, 0, TAU); ctx.fill(); } else ctx.fillRect(0, 0, w, h); }
        ctx.globalAlpha = 1;
        return;
      }
    }
    stats.nodes++;
    if (rec !== null && T.cache && rec.cost >= COST_MIN && (rec.flags & (F_BG | F_BLENDKID)) === 0) {
      if (tryCache(T, n, id, rec, type, w, h, op, blendOp, ma, mb, mc, md, me, mf, dx0, dy0, dx1, dy1)) return;
    }
    paintBody(T, n, id, v, rec, type, w, h, op, blendOp, ma, mb, mc, md, me, mf, dx0, dy0, dx1, dy1);
  }

  /* the node with matrix m: effects + group opacity / blend decide between drawing straight or through a layer */
  function paintBody(T, n, id, v, rec, type, w, h, op, blendOp, ma, mb, mc, md, me, mf, dx0, dy0, dx1, dy1) {
    if (type === 'INSTANCE' && v === null && rec !== null) { v = instTree(id, n, rec); n = v.n; }
    const fx = fxList(n);
    const scale = mb === 0 && mc === 0 ? Math.sqrt(Math.abs(ma * md)) : Math.sqrt(Math.abs(ma * md - mb * mc));
    const hasKids = CONT[type] === 1 && (v !== null ? v.kids.length > 0 : S().children(id).length > 0);
    if (fx === null) {
      if (op >= 1 && blendOp === 'source-over') { paintContent(T, n, id, v, rec, type, w, h, 1, null, scale, ma, mb, mc, md, me, mf); return; }
      if (!hasKids && paintCount(n, type) <= 1) {
        const ctx = T.ctx;
        if (blendOp !== 'source-over') ctx.globalCompositeOperation = blendOp;
        paintContent(T, n, id, v, rec, type, w, h, op, null, scale, ma, mb, mc, md, me, mf);
        if (blendOp !== 'source-over') ctx.globalCompositeOperation = 'source-over';
        ctx.globalAlpha = 1;
        return;
      }
      paintLayered(T, n, id, v, rec, type, w, h, op, blendOp, null, null, 0, scale, ma, mb, mc, md, me, mf, dx0, dy0, dx1, dy1);
      return;
    }
    let drops = null, inners = null, blur = 0, bg = 0;
    const lodFx = T.lod;
    for (let i = 0; i < fx.length; i++) {
      const e = fx[i], bl = Math.max(0, num(+e.blur, 0));
      if (e.type === 'drop') { if (lodFx && (bl + Math.abs(num(+e.x, 0)) + Math.abs(num(+e.y, 0)) + Math.abs(num(+e.spread, 0))) * scale < 0.7) continue; (drops || (drops = [])).push(e); }
      else if (e.type === 'inner') { if (lodFx && (bl + Math.abs(num(+e.x, 0)) + Math.abs(num(+e.y, 0))) * scale < 0.7) continue; (inners || (inners = [])).push(e); }
      else if (e.type === 'blur') { if (bl * scale >= 0.4) blur = Math.max(blur, bl); }
      else if (e.type === 'bgblur') bg = Math.max(bg, bl);
    }
    const g = type === 'TEXT' || type === 'GROUP' || type === 'LINE' ? null : geomOf(n, type, w, h, id, v, rec);
    const geo = g !== null && g.k !== R_PATH && anyVis(L.paints(n, 'fills'));
    if (bg > 0 && g !== null && HAS_FILTER && bg * scale >= 0.4) backdropBlur(T, g, w, h, bg * scale / 2, ma, mb, mc, md, me, mf);
    const needLayer = blur > 0 || (drops !== null && !geo) || ((op < 1 || blendOp !== 'source-over') && (hasKids || drops !== null || paintCount(n, type) > 1)) || (inners !== null && g === null);
    if (!needLayer) {
      const ctx = T.ctx;
      if (drops !== null) geoShadows(ctx, g, n, w, h, drops, scale, op, ma, mb, mc, md, me, mf);
      if (blendOp !== 'source-over') ctx.globalCompositeOperation = blendOp;
      paintContent(T, n, id, v, rec, type, w, h, op, inners, scale, ma, mb, mc, md, me, mf);
      if (blendOp !== 'source-over') ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
      return;
    }
    paintLayered(T, n, id, v, rec, type, w, h, op, blendOp, drops, inners, blur, scale, ma, mb, mc, md, me, mf, dx0, dy0, dx1, dy1, geo ? g : null);
  }
  function paintCount(n, type) {
    const c = countVis(L.paints(n, 'fills')) + countVis(L.paints(n, 'strokes'));
    return type === 'TEXT' && Array.isArray(n.runs) && n.runs.length ? Math.max(c, 1) : c;
  }

  function paintLayered(T, n, id, v, rec, type, w, h, op, blendOp, drops, inners, blur, scale, ma, mb, mc, md, me, mf, dx0, dy0, dx1, dy1, geo) {
    const ctx = T.ctx, B = T.bounds;
    let pad = 0;
    if (blur > 0) pad = Math.ceil(blur * scale * 1.5) + 2;
    if (drops !== null) for (let i = 0; i < drops.length; i++) { const e = drops[i]; pad = Math.max(pad, Math.ceil((Math.abs(num(+e.x, 0)) + Math.abs(num(+e.y, 0)) + num(+e.blur, 0) * 1.5 + Math.abs(num(+e.spread, 0))) * scale) + 2); }
    const lx0 = Math.max(Math.floor(dx0) - 1, B[0] - pad), ly0 = Math.max(Math.floor(dy0) - 1, B[1] - pad);
    const lx1 = Math.min(Math.ceil(dx1) + 1, B[2] + pad), ly1 = Math.min(Math.ceil(dy1) + 1, B[3] + pad);
    const LW = lx1 - lx0, LH = ly1 - ly0;
    if (LW <= 0 || LH <= 0) return;
    if (LW * LH > 1.3e8) { paintContent(T, n, id, v, rec, type, w, h, op, null, scale, ma, mb, mc, md, me, mf); ctx.globalAlpha = 1; return; }   /* too big for a layer: drawn plainly rather than not at all */
    const saveLD = LD;
    try {
      const F = getLayer(LW, LH);
      stats.layers++;
      const T2 = subT(T, F.ctx, lx0, ly0, LW, LH);
      const e2 = me - lx0, f2 = mf - ly0;
      if (drops !== null && geo) {
        geoShadows(F.ctx, geo, n, w, h, drops, scale, 1, ma, mb, mc, md, e2, f2);
        paintContent(T2, n, id, v, rec, type, w, h, 1, inners, scale, ma, mb, mc, md, e2, f2);
      } else if (drops !== null || (inners !== null && (type === 'TEXT' || type === 'GROUP'))) {
        const Cn = getLayer(LW, LH);
        stats.layers++;
        const T3 = subT(T, Cn.ctx, lx0, ly0, LW, LH);
        paintContent(T3, n, id, v, rec, type, w, h, 1, type === 'TEXT' || type === 'GROUP' ? null : inners, scale, ma, mb, mc, md, e2, f2);
        if (inners !== null && (type === 'TEXT' || type === 'GROUP')) alphaInner(Cn, LW, LH, inners, scale, ma, mb, mc, md);
        const fc = F.ctx;
        fc.setTransform(1, 0, 0, 1, 0, 0);
        if (drops !== null) for (let i = 0; i < drops.length; i++) {
          const s = drops[i], spr = num(+s.spread, 0) * scale, ld0 = LD;
          const src = Math.abs(spr) >= 0.3 ? spreadLayer(Cn, LW, LH, spr) : Cn;
          fc.save();
          fc.shadowColor = rgba(s.color || '#000000', s.opacity === undefined ? 0.25 : s.opacity);
          fc.shadowBlur = Math.max(0, num(+s.blur, 0)) * scale;
          fc.shadowOffsetX = FAR + (ma * num(+s.x, 0) + mc * num(+s.y, 0)); fc.shadowOffsetY = mb * num(+s.x, 0) + md * num(+s.y, 0);
          fc.drawImage(src.cv, 0, 0, LW, LH, -FAR, 0, LW, LH);
          fc.restore();
          LD = ld0;
        }
        fc.drawImage(Cn.cv, 0, 0, LW, LH, 0, 0, LW, LH);
      } else paintContent(T2, n, id, v, rec, type, w, h, 1, inners, scale, ma, mb, mc, md, e2, f2);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalAlpha = op;
      if (blendOp !== 'source-over') ctx.globalCompositeOperation = blendOp;
      if (blur > 0 && HAS_FILTER) ctx.filter = 'blur(' + (blur * scale / 2) + 'px)';
      ctx.drawImage(F.cv, 0, 0, LW, LH, lx0, ly0, LW, LH);
      if (blur > 0 && HAS_FILTER) ctx.filter = 'none';
      ctx.globalAlpha = 1;
      if (blendOp !== 'source-over') ctx.globalCompositeOperation = 'source-over';
    } finally { LD = saveLD; }
  }
  /* A picture grown (r > 0) or shrunk (r < 0) by r pixels all round: the "spread" of a shadow for everything that has
     no simple outline to grow (text, groups, paths, lines, boolean groups). It is stamped around a ring in steps that
     never leave a gap (1, 2, 4 ... pixels), so the edge is a 16-sided ring, round to about 2% of r. */
  function spreadLayer(src, LW, LH, r) {
    let A = getLayer(LW, LH), B = getLayer(LW, LH);
    stats.layers += 2;
    const ac = A.ctx;
    if (r > 0) ac.drawImage(src.cv, 0, 0, LW, LH, 0, 0, LW, LH);
    else { ac.fillStyle = '#000000'; ac.fillRect(0, 0, LW, LH); ac.globalCompositeOperation = 'destination-out'; ac.drawImage(src.cv, 0, 0, LW, LH, 0, 0, LW, LH); ac.globalCompositeOperation = 'source-over'; }
    let left = Math.abs(r), done = 0, guard = 0;
    while (left > 0.05 && guard++ < 14) {
      const step = Math.min(left, done === 0 ? 1 : 1 + done), N = step <= 1.5 ? 8 : 16, bc = B.ctx;
      bc.setTransform(1, 0, 0, 1, 0, 0); bc.globalCompositeOperation = 'source-over'; bc.clearRect(0, 0, LW, LH);
      bc.drawImage(A.cv, 0, 0, LW, LH, 0, 0, LW, LH);
      for (let k = 0; k < N; k++) { const a = k * TAU / N; bc.drawImage(A.cv, 0, 0, LW, LH, Math.cos(a) * step, Math.sin(a) * step, LW, LH); }
      const t = A; A = B; B = t;
      left -= step; done += step;
    }
    if (r > 0) return A;
    const bc = B.ctx;                                  /* shrunk = the picture without its grown outside */
    bc.setTransform(1, 0, 0, 1, 0, 0); bc.globalCompositeOperation = 'source-over'; bc.clearRect(0, 0, LW, LH);
    bc.drawImage(src.cv, 0, 0, LW, LH, 0, 0, LW, LH);
    bc.globalCompositeOperation = 'destination-out';
    bc.drawImage(A.cv, 0, 0, LW, LH, 0, 0, LW, LH);
    bc.globalCompositeOperation = 'source-over';
    return B;
  }
  /* shadows of a simple filled shape, drawn from its geometry: only the shadow lands (the shape itself is drawn far away) */
  function geoShadows(ctx, g, n, w, h, drops, scale, alpha, ma, mb, mc, md, me, mf) {
    let so = 0;
    const sp = L.paints(n, 'strokes');
    if (sp.length && anyVis(sp)) { const sw = Math.max(0, num(+G(n, 'strokeWeight'), 1)), al = G(n, 'strokeAlign'); so = al === 'outside' ? sw : al === 'inside' ? 0 : sw / 2; }
    for (let i = 0; i < drops.length; i++) {
      const s = drops[i];
      ctx.save();
      ctx.setTransform(ma, mb, mc, md, me - FAR, mf);
      ctx.shadowColor = rgba(s.color || '#000000', s.opacity === undefined ? 0.25 : s.opacity);
      ctx.shadowBlur = Math.max(0, num(+s.blur, 0)) * scale;
      ctx.shadowOffsetX = FAR + (ma * num(+s.x, 0) + mc * num(+s.y, 0)); ctx.shadowOffsetY = mb * num(+s.x, 0) + md * num(+s.y, 0);
      ctx.fillStyle = '#000000'; ctx.globalAlpha = alpha;
      fillGeom(ctx, g, w, h, num(+s.spread, 0) + so);
      ctx.restore();
    }
  }
  function geoInner(ctx, g, w, h, inners, scale, alpha, ma, mb, mc, md, me, mf) {
    for (let i = 0; i < inners.length; i++) {
      const s = inners[i], bl = Math.max(0, num(+s.blur, 0)), sx = num(+s.x, 0), sy = num(+s.y, 0), sp = num(+s.spread, 0);
      const m = Math.abs(sx) + Math.abs(sy) + bl * 2 + Math.abs(sp) + 8;
      ctx.save();
      ctx.setTransform(ma, mb, mc, md, me, mf);
      clipGeom(ctx, g, w, h);
      ctx.setTransform(ma, mb, mc, md, me - FAR, mf);
      ctx.shadowColor = rgba(s.color || '#000000', s.opacity === undefined ? 0.25 : s.opacity);
      ctx.shadowBlur = bl * scale;
      ctx.shadowOffsetX = FAR + (ma * sx + mc * sy); ctx.shadowOffsetY = mb * sx + md * sy;
      ctx.fillStyle = '#000000'; ctx.globalAlpha = alpha;
      if (g.k === R_PATH) { const q = new Path2D(); q.rect(-m, -m, w + 2 * m, h + 2 * m); q.addPath(g.p); ctx.fill(q, 'evenodd'); }
      else { ctx.beginPath(); ctx.rect(-m, -m, w + 2 * m, h + 2 * m); traceGeom(ctx, g, w, h, -sp); ctx.fill('evenodd'); }
      ctx.restore();
    }
  }
  /* inner shadow of anything (text, a group): the shadow of the picture's own inverse, kept inside the picture */
  function alphaInner(Cn, LW, LH, inners, scale, ma, mb, mc, md) {
    const I = getLayer(LW + 2, LH + 2), ic = I.ctx, cc = Cn.ctx;
    ic.fillStyle = '#000000';
    ic.fillRect(0, 0, LW + 2, LH + 2);
    ic.globalCompositeOperation = 'destination-out';
    ic.drawImage(Cn.cv, 0, 0, LW, LH, 1, 1, LW, LH);
    ic.globalCompositeOperation = 'source-over';
    cc.setTransform(1, 0, 0, 1, 0, 0);
    for (let i = 0; i < inners.length; i++) {
      const s = inners[i];
      cc.save();
      cc.globalCompositeOperation = 'source-atop';
      cc.shadowColor = rgba(s.color || '#000000', s.opacity === undefined ? 0.25 : s.opacity);
      cc.shadowBlur = Math.max(0, num(+s.blur, 0)) * scale;
      cc.shadowOffsetX = FAR + (ma * num(+s.x, 0) + mc * num(+s.y, 0)); cc.shadowOffsetY = mb * num(+s.x, 0) + md * num(+s.y, 0);
      cc.drawImage(I.cv, 0, 0, LW + 2, LH + 2, -1 - FAR, -1, LW + 2, LH + 2);
      cc.restore();
    }
  }
  /* background blur, best effort: what is already painted under the shape, blurred in place */
  function backdropBlur(T, g, w, h, sigma, ma, mb, mc, md, me, mf) {
    const ctx = T.ctx, cv = ctx.canvas;
    if (!cv || sigma <= 0) return;
    boxUnder(ma, mb, mc, md, me, mf, 0, 0, w, h);
    const pad = Math.ceil(sigma * 3) + 2;
    const sx = Math.max(0, Math.floor(BX[0]) - pad), sy = Math.max(0, Math.floor(BX[1]) - pad);
    const ex = Math.min(cv.width, Math.ceil(BX[2]) + pad), ey = Math.min(cv.height, Math.ceil(BX[3]) + pad);
    if (ex <= sx || ey <= sy) return;
    const saveLD = LD;
    try {
      const Lr = getLayer(ex - sx, ey - sy);
      Lr.ctx.drawImage(cv, sx, sy, ex - sx, ey - sy, 0, 0, ex - sx, ey - sy);
      ctx.save();
      ctx.setTransform(ma, mb, mc, md, me, mf);
      clipGeom(ctx, g, w, h);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalAlpha = 1;
      ctx.filter = 'blur(' + sigma + 'px)';
      ctx.drawImage(Lr.cv, 0, 0, ex - sx, ey - sy, sx, sy, ex - sx, ey - sy);
      ctx.filter = 'none';
      ctx.restore();
    } finally { LD = saveLD; }
  }

  function fillPaints(T, ctx, fills, g, w, h, alpha) {
    for (let i = 0; i < fills.length; i++) {
      const p = fills[i];
      if (!vis(p)) continue;
      if (p.type === 'image') { imagePaint(ctx, p, g, w, h, alpha); continue; }
      if (!usePaint(ctx, p, w, h, alpha, false)) continue;
      if (unitGrad(p, w, h)) {
        /* the shape as a clip, the gradient painted through the box's scale: an ellipse, exactly */
        const a = ctx.globalAlpha;
        ctx.save();
        clipGeom(ctx, g, w, h);
        ctx.globalAlpha = a;
        ctx.transform(w, 0, 0, h, 0, 0);
        ctx.fillRect(0, 0, 1, 1);
        ctx.restore();
        continue;
      }
      fillGeom(ctx, g, w, h, 0);
    }
  }
  /* Draw a silhouette (drawMask paints it in black, in the node's own space) and colour it with paints: for the cases a
     plain fill / stroke can not do - a gradient that needs the box's scale on a stroke or on text, a text stroke that
     stays inside or outside the letters. x0..y1 = the part of the node's space the silhouette can touch. */
  function maskDraw(ctx, paints, w, h, alpha, x0, y0, x1, y1, drawMask) {
    let m;
    try { const t = ctx.getTransform(); m = [t.a, t.b, t.c, t.d, t.e, t.f]; } catch (e) { return false; }
    boxUnder(m[0], m[1], m[2], m[3], m[4], m[5], x0, y0, x1, y1);
    const cv = ctx.canvas, cw = cv ? cv.width : 1e5, ch = cv ? cv.height : 1e5;
    const lx0 = Math.max(0, Math.floor(BX[0]) - 1), ly0 = Math.max(0, Math.floor(BX[1]) - 1), lx1 = Math.min(cw, Math.ceil(BX[2]) + 1), ly1 = Math.min(ch, Math.ceil(BX[3]) + 1);
    const LW = lx1 - lx0, LH = ly1 - ly0;
    if (LW <= 0 || LH <= 0 || LW * LH > 1.3e8) return true;
    const saveLD = LD;
    try {
      const M = getLayer(LW, LH), mc = M.ctx;
      stats.layers++;
      mc.setTransform(m[0], m[1], m[2], m[3], m[4] - lx0, m[5] - ly0);
      mc.fillStyle = '#000000'; mc.strokeStyle = '#000000';
      drawMask(mc);
      mc.setTransform(1, 0, 0, 1, 0, 0); mc.globalCompositeOperation = 'source-over'; mc.globalAlpha = 1; mc.setLineDash(NODASH);
      for (let i = 0; i < paints.length; i++) {
        const p = paints[i];
        if (!vis(p)) continue;
        const Pn = getLayer(LW, LH), pc = Pn.ctx;
        pc.drawImage(M.cv, 0, 0, LW, LH, 0, 0, LW, LH);
        pc.globalCompositeOperation = 'source-in';
        pc.setTransform(m[0], m[1], m[2], m[3], m[4] - lx0, m[5] - ly0);
        if (!usePaint(pc, p, w, h, 1, false)) { LD--; continue; }
        const pa = pc.globalAlpha;
        if (unitGrad(p, w, h)) { pc.transform(w, 0, 0, h, 0, 0); pc.fillRect(x0 / w, y0 / h, (x1 - x0) / w, (y1 - y0) / h); }
        else pc.fillRect(x0, y0, x1 - x0, y1 - y0);
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.globalAlpha = alpha * pa;
        ctx.drawImage(Pn.cv, 0, 0, LW, LH, lx0, ly0, LW, LH);
        ctx.restore();
        LD--;
      }
    } finally { LD = saveLD; }
    return true;
  }
  function imagePaint(ctx, p, g, w, h, alpha) {
    const im = image(p.hash);
    const a = alpha * (p.opacity === undefined ? 1 : p.opacity);
    if (!im || !(im.naturalWidth || im.width)) {
      ctx.globalAlpha = a; ctx.fillStyle = '#E3E3E8';
      fillGeom(ctx, g, w, h, 0);
      return;
    }
    const iw = im.naturalWidth || im.width, ih = im.naturalHeight || im.height, mode = p.mode || 'fill';
    ctx.globalAlpha = a;
    if (mode === 'tile') {
      let pat = null;
      try { pat = ctx.createPattern(im, 'repeat'); const sc = num(+p.scale, 1); if (pat && sc !== 1 && pat.setTransform) pat.setTransform(new DOMMatrix([sc, 0, 0, sc, 0, 0])); } catch (e) { pat = null; }
      if (pat) { ctx.fillStyle = pat; fillGeom(ctx, g, w, h, 0); }
      return;
    }
    const plain = g.k === R_RECT;
    if (!plain) { ctx.save(); clipGeom(ctx, g, w, h); ctx.globalAlpha = a; }
    if (mode === 'fit') {
      const s = Math.min(w / iw, h / ih), dw = iw * s, dh = ih * s;
      ctx.drawImage(im, (w - dw) / 2, (h - dh) / 2, dw, dh);
    } else {
      let sx = 0, sy = 0, sw = iw, sh = ih;
      if (mode === 'crop' && Array.isArray(p.crop) && p.crop.length === 4) {
        sx = Math.max(0, Math.min(1, +p.crop[0] || 0)) * iw; sy = Math.max(0, Math.min(1, +p.crop[1] || 0)) * ih;
        sw = Math.max(1, Math.min(iw - sx, (+p.crop[2] || 1) * iw)); sh = Math.max(1, Math.min(ih - sy, (+p.crop[3] || 1) * ih));
      }
      /* cover: the middle part of the source that has the box's shape */
      if (w > 0 && h > 0) {
        const want = w / h, have = sw / sh;
        if (have > want) { const nw = sh * want; sx += (sw - nw) / 2; sw = nw; } else { const nh = sw / want; sy += (sh - nh) / 2; sh = nh; }
        ctx.drawImage(im, sx, sy, sw, sh, 0, 0, w, h);
      }
    }
    if (!plain) ctx.restore();
  }
  function strokePaints(ctx, n, strokes, g, w, h, alpha) {
    const sw = num(+G(n, 'strokeWeight'), 1);
    if (!(sw > 0)) return;
    let align = G(n, 'strokeAlign') || 'center';
    if (g.open) align = 'center';
    ctx.lineCap = G(n, 'strokeCap') || 'butt';
    ctx.lineJoin = G(n, 'strokeJoin') || 'miter';
    ctx.miterLimit = 4;
    const dash = G(n, 'dash'), hasDash = Array.isArray(dash) && dash.length > 0;
    if (hasDash) ctx.setLineDash(dash);
    for (let i = 0; i < strokes.length; i++) {
      const p = strokes[i];
      if (!vis(p)) continue;
      if (unitGrad(p, w, h)) {
        const cap = ctx.lineCap, join = ctx.lineJoin, o = sw * 2 + 2;
        maskDraw(ctx, [p], w, h, alpha, -o, -o, w + o, h + o, (mc) => { mc.lineCap = cap; mc.lineJoin = join; mc.miterLimit = 4; if (hasDash) mc.setLineDash(dash); strokeGeom(mc, g, w, h, sw, align); });
        continue;
      }
      if (!usePaint(ctx, p, w, h, alpha, true)) continue;
      strokeGeom(ctx, g, w, h, sw, align);
    }
    if (hasDash) ctx.setLineDash(NODASH);
  }

  /* fills, inner shadows, children, strokes of one node, drawn with matrix m (no group opacity here) */
  function paintContent(T, n, id, v, rec, type, w, h, alpha, inners, scale, ma, mb, mc, md, me, mf) {
    const ctx = T.ctx;
    if (type === 'TEXT') { ctx.setTransform(ma, mb, mc, md, me, mf); paintText(T, ctx, n, rec, w, h, alpha, scale); return; }
    if (type === 'GROUP' || type === 'PAGE') { paintKidsFrom(T, id, v, 0, ma, mb, mc, md, me, mf); return; }
    const g = geomOf(n, type, w, h, id, v, rec);
    const fills = L.paints(n, 'fills');
    if (fills.length !== 0 && g.k !== R_LINE) {
      ctx.setTransform(ma, mb, mc, md, me, mf);
      /* the common case, written out: one solid colour in a plain box */
      if (fills.length === 1 && g.k === R_RECT && fills[0] !== null && fills[0].type === 'solid' && fills[0].visible !== false) {
        ctx.globalAlpha = alpha; ctx.fillStyle = rgba(fills[0].color, fills[0].opacity); ctx.fillRect(0, 0, w, h);
      } else fillPaints(T, ctx, fills, g, w, h, alpha);
    }
    if (inners !== null && g.k !== R_LINE) geoInner(ctx, g, w, h, inners, scale, alpha, ma, mb, mc, md, me, mf);
    if (CONT[type] === 1) {
      const has = v !== null ? v.kids.length > 0 : S().children(id).length > 0;
      if (has) {
        const clip = clips(n);
        if (clip) { ctx.save(); ctx.setTransform(ma, mb, mc, md, me, mf); clipGeom(ctx, g, w, h); }
        if (v !== null && (v.sx !== 1 || v.sy !== 1)) paintKidsFrom(T, id, v, 0, ma * v.sx, mb * v.sx, mc * v.sy, md * v.sy, me, mf);
        else paintKidsFrom(T, id, v, 0, ma, mb, mc, md, me, mf);
        if (clip) ctx.restore();
      }
    }
    const strokes = L.paints(n, 'strokes');
    if (strokes.length !== 0) { ctx.setTransform(ma, mb, mc, md, me, mf); strokePaints(ctx, n, strokes, g, w, h, alpha); }
    ctx.globalAlpha = 1;
  }

  function textSeg(ctx, s, y, stroke) {
    const st = s.st;
    L.setFont(ctx, st);
    if (!L.hasLetterSpacing && st.ls) {
      let x = s.x;
      for (const ch of Array.from(s.text)) { if (stroke) ctx.strokeText(ch, x, y); else ctx.fillText(ch, x, y); x += ctx.measureText(ch).width + st.ls; }
    } else if (stroke) ctx.strokeText(s.text, s.x, y); else ctx.fillText(s.text, s.x, y);
  }
  function textPass(ctx, lay, own, stroke) {
    for (let i = 0; i < lay.lines.length; i++) {
      const ln = lay.lines[i], sg = ln.segs;
      for (let j = 0; j < sg.length; j++) {
        const s = sg[j], st = s.st;
        if ((st.fills !== undefined) !== own) continue;
        if (!(s.sp && st.deco === 'none')) { if (!s.sp) textSeg(ctx, s, ln.base, stroke); }
        if (st.deco !== 'none' && !stroke) {
          const th = Math.max(1, st.size / 14);
          if (st.deco === 'underline') ctx.fillRect(s.x, ln.base + st.size * 0.1, s.w, th);
          else if (st.deco === 'strike') ctx.fillRect(s.x, ln.base - st.size * 0.3, s.w, th);
        }
      }
    }
  }
  function paintText(T, ctx, n, rec, w, h, alpha, scale) {
    const lay = rec !== null && rec.tl !== null ? rec.tl : L.textLayout(n);
    if (!lay.lines.length) return;
    const fills = L.paints(n, 'fills');
    if (T.lod) {
      const px = num(+G(n, 'fontSize'), 16) * scale;
      if (px < 0.9) return;
      if (px < 2.7) {
        /* too small to read: one soft bar per line */
        const col = flatColor(n, 0);
        if (col === null) return;
        ctx.fillStyle = col; ctx.globalAlpha = alpha * 0.4;
        for (let i = 0; i < lay.lines.length; i++) { const ln = lay.lines[i]; if (ln.w > 0) ctx.fillRect(ln.x, ln.y + ln.h * 0.3, ln.w, ln.h * 0.4); }
        ctx.globalAlpha = 1;
        return;
      }
    }
    for (let i = 0; i < lay.lines.length; i++) { const sg = lay.lines[i].segs; for (let j = 0; j < sg.length; j++) if (!famReady(sg[j].st.font)) needFont(sg[j].st); }
    ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
    const strokes = L.paints(n, 'strokes'), sw = num(+G(n, 'strokeWeight'), 1);
    const hasStroke = strokes.length !== 0 && sw > 0 && anyVis(strokes), sAlign = hasStroke ? (G(n, 'strokeAlign') || 'center') : 'center';
    const join = G(n, 'strokeJoin') === 'miter' ? 'miter' : 'round';
    /* where the letters (and their stroke) can reach, in the node's own space */
    let bx0 = 0, by0 = 0, bx1 = w, by1 = h;
    const slop = num(+G(n, 'fontSize'), 16) * 0.5 + (hasStroke ? sw * 2 + 2 : 0);
    for (let i = 0; i < lay.lines.length; i++) { const ln = lay.lines[i]; bx0 = Math.min(bx0, ln.x - slop); bx1 = Math.max(bx1, ln.x + ln.w + slop); by0 = Math.min(by0, ln.y - slop); by1 = Math.max(by1, ln.y + ln.h + slop); }
    const tb = (c) => { c.textBaseline = 'alphabetic'; c.textAlign = 'left'; };
    const doStroke = (width) => {
      ctx.lineJoin = join; ctx.miterLimit = 4; ctx.lineWidth = width;
      for (let i = 0; i < strokes.length; i++) {
        const p = strokes[i];
        if (!vis(p)) continue;
        if (unitGrad(p, w, h)) { maskDraw(ctx, [p], w, h, alpha, bx0, by0, bx1, by1, (mc) => { tb(mc); mc.lineJoin = join; mc.miterLimit = 4; mc.lineWidth = width; textPass(mc, lay, false, true); textPass(mc, lay, true, true); }); continue; }
        if (usePaint(ctx, p, w, h, alpha, true)) { textPass(ctx, lay, false, true); textPass(ctx, lay, true, true); }
      }
    };
    let ownRuns = false;
    for (let i = 0; i < lay.lines.length && !ownRuns; i++) { const sg = lay.lines[i].segs; for (let j = 0; j < sg.length; j++) if (sg[j].st.fills !== undefined) { ownRuns = true; break; } }
    for (let i = 0; i < fills.length; i++) {
      const p = fills[i];
      if (!vis(p)) continue;
      if (unitGrad(p, w, h)) { maskDraw(ctx, [p], w, h, alpha, bx0, by0, bx1, by1, (mc) => { tb(mc); textPass(mc, lay, false, false); }); continue; }
      if (usePaint(ctx, p, w, h, alpha, false)) textPass(ctx, lay, false, false);
    }
    if (ownRuns) {
      for (let i = 0; i < lay.lines.length; i++) {
        const ln = lay.lines[i], sg = ln.segs;
        for (let j = 0; j < sg.length; j++) {
          const s = sg[j], rf = s.st.fills;
          if (rf === undefined || !Array.isArray(rf)) continue;
          for (let k = 0; k < rf.length; k++) {
            const p = rf[k];
            if (!vis(p) || !usePaint(ctx, p, w, h, alpha, false)) continue;
            if (!s.sp) textSeg(ctx, s, ln.base, false);
            if (s.st.deco !== 'none') { const th = Math.max(1, s.st.size / 14); ctx.fillRect(s.x, s.st.deco === 'underline' ? ln.base + s.st.size * 0.1 : ln.base - s.st.size * 0.3, s.w, th); }
          }
        }
      }
    }
    if (hasStroke && sAlign === 'center') doStroke(sw);
    else if (hasStroke) {
      /* a stroke that stays inside (or outside) the letters: twice as wide, then cut by the letters themselves */
      const inside = sAlign === 'inside';
      maskDraw(ctx, strokes, w, h, alpha, bx0, by0, bx1, by1, (mc) => {
        tb(mc); mc.lineJoin = join; mc.miterLimit = 4; mc.lineWidth = sw * 2;
        textPass(mc, lay, false, true); textPass(mc, lay, true, true);
        mc.globalCompositeOperation = inside ? 'destination-in' : 'destination-out';
        if (inside) {
          /* destination-in keeps only what the LAST drawn piece covers: so cut with one picture of all the letters */
          const saveLD2 = LD, cvs = mc.canvas, G2 = getLayer(cvs.width, cvs.height), gc = G2.ctx;
          try { gc.setTransform(mc.getTransform()); tb(gc); gc.fillStyle = '#000000'; textPass(gc, lay, false, false); textPass(gc, lay, true, false);
            mc.save(); mc.setTransform(1, 0, 0, 1, 0, 0); mc.drawImage(G2.cv, 0, 0); mc.restore(); } finally { LD = saveLD2; }
        } else { textPass(mc, lay, false, false); textPass(mc, lay, true, false); }
      });
    }
    ctx.globalAlpha = 1;
  }

  /* ------------------------------------------------------------------ what changed -> what must be painted again */
  function bumpUp(p, stamp, t) {
    const s = S();
    let g = 0;
    while (p !== undefined && p !== null && g++ < 2000) {
      let r = D.get(p);
      if (r === undefined) { const n = s.get(p); if (!n) return; r = newRec(n.parent); D.set(p, r); }
      if (r.cv === stamp) return;
      r.cv = stamp; r.hot = t + HOT_MS;
      p = r.par;
    }
  }
  function classify(ps) {
    if (!ps || typeof ps.forEach !== 'function') return 2;
    let c = 0;
    for (const k of ps) { if (NONVIS[k] === 1) continue; if (POSONLY[k] === 1) { if (c < 1) c = 1; } else return 2; }
    return c;
  }
  function inComponent(n) {
    const s = S();
    let c = n, g = 0;
    while (c && g++ < 2000) { if (c.type === 'COMPONENT' || c.type === 'COMPONENT_SET') return true; c = c.parent ? s.get(c.parent) : null; }
    return false;
  }
  /* where this node's pixels are right now: its own last painted place, or the freshest ancestor that covered it */
  function addOld(r) {
    if (r === undefined || sceneFull) return;
    let best = r.serial > 0 ? r : null, fxa = null, p = r.par, g = 0;
    while (p !== undefined && p !== null && g++ < 2000) {
      const pr = D.get(p);
      if (pr === undefined) break;
      if (pr.serial > 0) { if (best === null || pr.serial > best.serial) best = pr; if ((pr.flags & (F_FX | F_MASKKID)) !== 0) fxa = pr; }
      p = pr.par;
    }
    if (fxa !== null) best = fxa;
    if (best !== null) damage.push([best.wx0, best.wy0, best.wx1, best.wy1]);
  }
  function onChange(ev) {
    if (!ev || !ev.ids) return;
    const s = S(), t = now(), stamp = ++clock;
    const props = ev.props && typeof ev.props.get === 'function' ? ev.props : null;
    let any = false;
    for (const id of ev.ids) {
      const n = s.get(id), r = D.get(id);
      if (n === undefined) {
        gridIds.delete(id);
        if (r !== undefined) { addOld(r); bumpUp(r.par, stamp, t); D.delete(id); }
        const en = C.get(id);
        if (en !== undefined) dropEntry(id, en);
        pruneDue = true; any = true;
        continue;
      }
      if (Array.isArray(n.grids) && n.grids.length) gridIds.add(id); else if (gridIds.size) gridIds.delete(id);
      if (n.type === 'DOCUMENT') { resEpoch++; clearCache(); sceneFull = true; any = true; continue; }
      if (n.type === 'PAGE') { sceneFull = true; any = true; if (r !== undefined) r.cv = stamp; continue; }
      const ps = props ? props.get(id) : null, cls = classify(ps);
      if (cls === 0) { overlayDirty = true; continue; }
      any = true;
      addOld(r);
      const rr = r !== undefined ? r : recOf(id, n);
      if (rr.par !== n.parent) { bumpUp(rr.par, stamp, t); rr.par = n.parent; }
      if (cls === 2 || r === undefined) { rr.cv = stamp; rr.hot = t + HOT_MS; }
      bumpUp(n.parent, stamp, t);
      if (instSeen && inComponent(n)) { compEpoch++; sceneFull = true; }
      if (n.mask === true || (ps && typeof ps.has === 'function' && ps.has('mask'))) sceneFull = true;
      pending.add(id);
    }
    if (any) lastChangeAt = t;
    if (ev.structural) pruneDue = true;
    schedule();
  }
  function onLoad() {
    D.clear(); clearCache(); pending.clear(); damage = []; gridIds.clear(); gridScan = true;
    resEpoch++; compEpoch++; instSeen = false; sceneFull = true; last.valid = false;
    schedule();
  }
  function prune() {
    pruneDue = false;
    const s = S();
    if (D.size < 64) return;
    for (const id of D.keys()) if (!s.has(id)) D.delete(id);
    for (const [id, en] of C) if (!s.has(id)) dropEntry(id, en);
  }

  /* ------------------------------------------------------------------ the frame */
  function schedule() { if (!raf && canvas) raf = requestAnimationFrame(frame); }
  function emit(evt, arg) { const l = listeners[evt]; if (l) for (let i = 0; i < l.length; i++) { try { l[i](arg); } catch (e) { if (window.console) console.error('[HD.render]', e); } } }
  function snap(v) { return Math.round(v * dpr) / dpr; }
  function syncSize() {
    if (!canvas) return false;
    const ndpr = Math.max(1, Math.min(4, window.devicePixelRatio || 1));
    const w = Math.max(1, Math.round(canvas.clientWidth || cssW || 1)), h = Math.max(1, Math.round(canvas.clientHeight || cssH || 1));
    const pw = Math.max(1, Math.round(w * ndpr)), ph = Math.max(1, Math.round(h * ndpr));
    if (pw === canvas.width && ph === canvas.height && ndpr === dpr && scene.width === pw && scene.height === ph) { cssW = w; cssH = h; return false; }
    dpr = ndpr; cssW = w; cssH = h;
    canvas.width = pw; canvas.height = ph;
    scene.width = pw; scene.height = ph;
    sceneFull = true; last.valid = false;
    return true;
  }
  function stepAnim(t) {
    if (!anim) return false;
    let k = (t - anim.t0) / anim.dur;
    if (k >= 1) k = 1;
    const e = 1 - Math.pow(1 - k, 3);
    const z = Math.exp(anim.lz0 + (anim.lz1 - anim.lz0) * e);
    const cx = anim.cx0 + (anim.cx1 - anim.cx0) * e, cy = anim.cy0 + (anim.cy1 - anim.cy0) * e;
    view.zoom = k === 1 ? anim.z1 : z;
    view.x = snap(cssW / 2 - cx * view.zoom); view.y = snap(cssH / 2 - cy * view.zoom);
    if (k === 1) { view.x = snap(anim.x1); view.y = snap(anim.y1); anim = null; return true; }
    schedule();
    return false;
  }
  function paintScene(regions, pageId, pn, bs, tx, ty, exact, canBuild, t0) {
    const ctx = sctx, Wd = scene.width, Hd = scene.height;
    LD = 0;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
    const bg = pn ? rgba(G(pn, 'bg') || '#F5F5F5', 1) : '#F5F5F5';
    let cl, bounds;
    if (regions === null) { cl = [0, 0, Wd, Hd]; bounds = cl; ctx.fillStyle = bg; ctx.fillRect(0, 0, Wd, Hd); }
    else {
      if (!regions.length) return null;
      let bx0 = Infinity, by0 = Infinity, bx1 = -Infinity, by1 = -Infinity;
      ctx.save();
      ctx.beginPath();
      for (let i = 0; i < regions.length; i += 4) {
        ctx.rect(regions[i], regions[i + 1], regions[i + 2] - regions[i], regions[i + 3] - regions[i + 1]);
        bx0 = Math.min(bx0, regions[i]); by0 = Math.min(by0, regions[i + 1]); bx1 = Math.max(bx1, regions[i + 2]); by1 = Math.max(by1, regions[i + 3]);
      }
      ctx.clip();
      ctx.fillStyle = bg;
      ctx.fillRect(bx0, by0, bx1 - bx0, by1 - by0);
      cl = regions; bounds = [bx0, by0, bx1, by1];
    }
    const T = {ctx, clips: cl, bounds, lod: !debug.noLod, cache: !debug.noCache, canBuild, record: true, exact, bs, btx: tx, bty: ty,
      serial: ++serial, budgetEnd: t0 + (exact ? 45 : 7), now: t0, root: null, inexact: false, backdrop: true};
    try { if (pn) paintKidsFrom(T, pageId, null, 0, bs, 0, 0, bs, tx, ty); }
    finally { if (regions !== null) ctx.restore(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'; }
    return T;
  }
  function worldExtOf(id) {
    const s = S();
    let n = s.get(id);
    if (!n || n.type === 'PAGE' || n.type === 'DOCUMENT') return null;
    /* an ancestor with effects or a mask repaints as a whole */
    let target = id, p = n.parent, g = 0;
    while (p && g++ < 2000) { const pn = s.get(p); if (!pn || pn.type === 'PAGE' || pn.type === 'DOCUMENT') break; const pr = D.get(p); if (pn.effects !== undefined || pn.effectStyle !== undefined || (pr !== undefined && (pr.flags & (F_FX | F_MASKKID)) !== 0)) target = p; p = pn.parent; }
    n = s.get(target);
    if (n.visible === false) return null;
    const r = derive(target, n), m = worldMat(target);
    boxUnder(m[0], m[1], m[2], m[3], m[4], m[5], r.x0, r.y0, r.x1, r.y1);
    return [BX[0], BX[1], BX[2], BX[3]];
  }
  function frame() {
    raf = 0;
    if (!canvas || !sctx) return;
    const t0 = now();
    const animEnded = stepAnim(t0);
    const resized = syncSize();
    if (pruneDue && D.size > 0) prune();
    const s = S(), page = HD.sel && HD.sel.page ? HD.sel.page : null, pn = page && s ? s.get(page) : null;
    if (view.x !== snap(view.x)) view.x = snap(view.x);
    if (view.y !== snap(view.y)) view.y = snap(view.y);
    if (!(view.zoom > 0)) view.zoom = 1;
    const bs = dpr * view.zoom, tx = Math.round(view.x * dpr), ty = Math.round(view.y * dpr);
    const Wd = scene.width, Hd = scene.height;
    const viewChanged = !last.valid || bs !== last.s || tx !== last.tx || ty !== last.ty;
    let did = '';
    stats.nodes = 0; stats.culled = 0; stats.flat = 0; stats.blits = 0; stats.built = 0; stats.layers = 0; stats.regions = 0;
    /* a heavy page being zoomed: show the last picture scaled now, paint the real one when the zoom rests (or every ~1/3 s) */
    if (last.valid && bs !== last.s && !resized && !sceneFull && !forceReal && !animEnded && !wantExact && pending.size === 0 && damage.length === 0 &&
        page === last.page && lastFullMs > 8 && api.zoomPreview !== false) {
      const k = bs / last.s;
      if (k > 0.45 && k < 2.2 && !(t0 - lastZoomAt < 120 && t0 - lastRealAt > 320)) {
        if (bs !== pvScale) {                        /* only a frame that really zoomed pushes the real paint further away */
          pvScale = bs; lastZoomAt = t0;
          clearTimeout(zoomTimer);
          zoomTimer = setTimeout(() => { zoomTimer = 0; forceReal = true; schedule(); }, 90);
        }
        present(pn, page, bs, tx, ty, {k, ox: tx - last.tx * k, oy: ty - last.ty * k});
        stats.ms = now() - t0; stats.mode = 'preview'; stats.frames++;
        emit('view', view);
        emit('frame', stats);
        return;
      }
    }
    forceReal = false; pvScale = 0;
    if (sceneFull || viewChanged || page !== last.page || pending.size > 0 || damage.length > 0) {
      let full = sceneFull || !last.valid || page !== last.page || bs !== last.s || debug.noDirty;
      const zooming = last.valid && bs !== last.s;
      if (zooming) lastZoomAt = t0;
      /* loose = something is moving (a zoom, an edit just now): a bitmap may be shown scaled or between pixels for a
         moment; otherwise every bitmap is shown 1:1 or the node is drawn straight */
      const loose = zooming || t0 - lastZoomAt < 150 || t0 - lastChangeAt < 250;
      const exact = !loose || (wantExact && !zooming);
      let regions = null;
      if (!full && pn) { const pr = derive(page, pn); if ((pr.flags & F_BG) !== 0) full = true; }
      if (!full && pending.size > 600) full = true;
      if (!full) {
        regions = [];
        const dx = tx - last.tx, dy = ty - last.ty;
        if (dx !== 0 || dy !== 0) {
          if (debug.noBlit || Math.abs(dx) >= Wd || Math.abs(dy) >= Hd) full = true;
          else {
            sctx.setTransform(1, 0, 0, 1, 0, 0);
            sctx.globalAlpha = 1; sctx.globalCompositeOperation = 'copy';
            sctx.drawImage(scene, dx, dy);
            sctx.globalCompositeOperation = 'source-over';
            if (dx > 0) regions.push(0, 0, dx, Hd); else if (dx < 0) regions.push(Wd + dx, 0, Wd, Hd);
            if (dy > 0) regions.push(0, 0, Wd, dy); else if (dy < 0) regions.push(0, Hd + dy, Wd, Hd);
          }
        }
      }
      if (!full) {
        const dm = [];
        const add = (r) => {
          const x0 = Math.max(0, Math.floor(r[0] * bs + tx) - 2), y0 = Math.max(0, Math.floor(r[1] * bs + ty) - 2);
          const x1 = Math.min(Wd, Math.ceil(r[2] * bs + tx) + 2), y1 = Math.min(Hd, Math.ceil(r[3] * bs + ty) + 2);
          if (x1 > x0 && y1 > y0) dm.push(x0, y0, x1, y1);
        };
        for (let i = 0; i < damage.length; i++) add(damage[i]);
        for (const id of pending) { const r = worldExtOf(id); if (r !== null) add(r); }
        if (dm.length > 4 * 14) {
          let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
          for (let i = 0; i < dm.length; i += 4) { x0 = Math.min(x0, dm[i]); y0 = Math.min(y0, dm[i + 1]); x1 = Math.max(x1, dm[i + 2]); y1 = Math.max(y1, dm[i + 3]); }
          dm.length = 0; dm.push(x0, y0, x1, y1);
        }
        let area = 0;
        for (let i = 0; i < dm.length; i += 4) { area += (dm[i + 2] - dm[i]) * (dm[i + 3] - dm[i + 1]); regions.push(dm[i], dm[i + 1], dm[i + 2], dm[i + 3]); }
        if (area > Wd * Hd * 0.65) full = true;
      }
      pending.clear(); damage = [];
      const T = paintScene(full ? null : regions, page, pn, bs, tx, ty, exact, !zooming, t0);
      did = full ? 'full' : (regions.length ? 'part' : 'none');
      lastRealAt = now();
      if (full) lastFullMs = lastRealAt - t0;
      stats.regions = full ? 0 : regions.length / 4;
      if (exact && full) { wantExact = false; if (settleTimer) { clearTimeout(settleTimer); settleTimer = 0; } }
      if (T !== null && T.inexact) { clearTimeout(settleTimer); settleTimer = setTimeout(() => { settleTimer = 0; wantExact = true; sceneFull = true; schedule(); }, 220); }
      sceneFull = false;
      last.s = bs; last.tx = tx; last.ty = ty; last.page = page; last.w = Wd; last.h = Hd; last.valid = true;
      if (debug.showDamage && !full && regions) last.dbg = regions.slice(); else last.dbg = null;
      trimPool();
    }
    present(pn, page, bs, tx, ty, null);
    overlayDirty = false;
    stats.ms = now() - t0; stats.mode = did || 'overlay'; stats.frames++;
    stats.cacheMB = Math.round(cacheBytes / 1048576 * 10) / 10; stats.cacheN = C.size;
    if (viewChanged) emit('view', view);
    emit('frame', stats);
  }
  const labelFit = new Map();
  function fitLabel(c, name, maxW) {
    const k = name + '\u0001' + Math.round(maxW);
    let v = labelFit.get(k);
    if (v !== undefined) return v;
    v = name;
    if (c.measureText(v).width > maxW) {
      let lo = 0, hi = name.length;
      while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (c.measureText(name.slice(0, mid) + '\u2026').width <= maxW) lo = mid; else hi = mid - 1; }
      v = lo > 0 ? name.slice(0, lo) + '\u2026' : '';
    }
    if (labelFit.size > 3000) labelFit.clear();
    labelFit.set(k, v);
    return v;
  }
  /* layout grids: `grids` on a frame = [{type: 'grid' | 'columns' | 'rows', size, count, gutter, margin, align, color,
     opacity, visible}], drawn over the picture inside the frame's box. Never part of the scene, a bitmap or an export. */
  function gridSpans(g, total) {
    const count = Math.max(1, Math.min(200, Math.round(num(+g.count, 5)))), gut = Math.max(0, num(+g.gutter, 20)), mar = Math.max(0, num(+g.margin, 0));
    const al = g.align === 'start' || g.align === 'center' || g.align === 'end' ? g.align : 'stretch';
    let size = Math.max(0, num(+g.size, 0)), at = mar;
    if (al === 'stretch' || !(size > 0)) size = Math.max(0, (total - 2 * mar - gut * (count - 1)) / count);
    else { const all = size * count + gut * (count - 1); at = al === 'center' ? (total - all) / 2 : al === 'end' ? total - mar - all : mar; }
    const out = [];
    for (let i = 0; i < count; i++) out.push(at + i * (size + gut), size);
    return out;
  }
  function drawGrids(c, page, bs, tx, ty) {
    const s = S();
    if (gridScan) { gridScan = false; if (s.walk && s.ROOT && s.has(s.ROOT)) { let g = 0; s.walk(s.ROOT, (id) => { const n = s.get(id); if (g++ < 400000 && n && Array.isArray(n.grids) && n.grids.length) gridIds.add(id); }); } }
    if (!gridIds.size) return;
    for (const id of gridIds) {
      const n = s.get(id);
      if (!n || !Array.isArray(n.grids) || n.visible === false || n.type === 'PAGE' || n.type === 'DOCUMENT') continue;
      let onPage = false, hidden = false, c0 = n.parent, g0 = 0;
      while (c0 && g0++ < 2000) { const pn = s.get(c0); if (!pn) break; if (c0 === page) { onPage = true; break; } if (pn.visible === false) { hidden = true; break; } c0 = pn.parent; }
      if (!onPage || hidden) continue;
      const m = worldMat(id), w = W(n), h = H(n);
      boxUnder(m[0] * bs, m[1] * bs, m[2] * bs, m[3] * bs, m[4] * bs + tx, m[5] * bs + ty, 0, 0, w, h);
      if (BX[2] < 0 || BX[3] < 0 || BX[0] > canvas.width || BX[1] > canvas.height) continue;
      const k = Math.sqrt(Math.abs(m[0] * m[3] - m[1] * m[2])) * bs;      /* device pixels per layer unit */
      c.save();
      c.setTransform(m[0] * bs, m[1] * bs, m[2] * bs, m[3] * bs, m[4] * bs + tx, m[5] * bs + ty);
      c.beginPath(); c.rect(0, 0, w, h); c.clip();
      for (let i = 0; i < n.grids.length; i++) {
        const g = n.grids[i];
        if (!g || g.visible === false) continue;
        const type = g.type === 'columns' || g.type === 'rows' ? g.type : 'grid';
        c.fillStyle = rgba(typeof g.color === 'string' ? g.color : '#FF0000', Math.max(0, Math.min(1, num(+g.opacity, 0.1))));
        if (type === 'grid') {
          const sz = Math.max(1, num(+g.size, 10)), lw = 1 / k;
          if (sz * k < 4 || w / sz > 4000 || h / sz > 4000) continue;            /* too fine to tell apart at this zoom */
          for (let x = sz; x < w - 0.001; x += sz) c.fillRect(x - lw / 2, 0, lw, h);
          for (let y = sz; y < h - 0.001; y += sz) c.fillRect(0, y - lw / 2, w, lw);
        } else {
          const sp = gridSpans(g, type === 'columns' ? w : h);
          for (let j = 0; j < sp.length; j += 2) { if (type === 'columns') c.fillRect(sp[j], 0, sp[j + 1], h); else c.fillRect(0, sp[j], w, sp[j + 1]); }
        }
      }
      c.restore();
    }
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  function present(pn, page, bs, tx, ty, pv) {
    const c = vctx, s = S();
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.globalAlpha = 1;
    if (pv === null) { c.globalCompositeOperation = 'copy'; c.drawImage(scene, 0, 0); c.globalCompositeOperation = 'source-over'; }
    else {
      c.globalCompositeOperation = 'source-over';
      c.fillStyle = pn ? rgba(G(pn, 'bg') || '#F5F5F5', 1) : '#F5F5F5';
      c.fillRect(0, 0, canvas.width, canvas.height);
      c.setTransform(pv.k, 0, 0, pv.k, pv.ox, pv.oy);
      c.drawImage(scene, 0, 0);
      c.setTransform(1, 0, 0, 1, 0, 0);
    }
    /* pixel grid */
    if (view.zoom >= 8 && api.pixelGrid !== false) {
      const Wd = canvas.width, Hd = canvas.height;
      c.beginPath();
      for (let wx = Math.ceil(-tx / bs); wx * bs + tx < Wd; wx++) { const x = Math.round(wx * bs + tx) + 0.5; c.moveTo(x, 0); c.lineTo(x, Hd); }
      for (let wy = Math.ceil(-ty / bs); wy * bs + ty < Hd; wy++) { const y = Math.round(wy * bs + ty) + 0.5; c.moveTo(0, y); c.lineTo(Wd, y); }
      c.strokeStyle = 'rgba(128,128,128,0.16)'; c.lineWidth = 1;
      c.stroke();
    }
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    /* names of the top-level frames, in screen space */
    labelRects = [];
    if (pn && api.frameLabels !== false) {
      const ks = s.children(page), z = view.zoom, vx = tx / dpr, vy = ty / dpr;
      c.font = '11px Inter, system-ui, -apple-system, "Segoe UI", sans-serif';
      c.textBaseline = 'alphabetic'; c.textAlign = 'left';
      for (let i = 0; i < ks.length; i++) {
        const n = s.get(ks[i]);
        if (n === undefined || LABELED[n.type] !== 1 || n.visible === false) continue;
        const sw = W(n) * z;
        if (sw < 34) continue;
        localMat(n, LM);
        const sx = LM[4] * z + vx, sy = LM[5] * z + vy;
        if (!n.rot && (sx > cssW || sy < 0 || sy > cssH + 20 || sx + sw < 0)) continue;
        const name = typeof n.name === 'string' ? n.name : '';
        if (!name) continue;
        const txt = fitLabel(c, name.length > 80 ? name.slice(0, 80) : name, sw);
        if (!txt) continue;
        const sel = HD.sel && HD.sel.has && HD.sel.has(ks[i]);
        c.fillStyle = sel ? '#6D4AFF' : (n.type === 'COMPONENT' || n.type === 'COMPONENT_SET' || n.type === 'INSTANCE') ? '#8B3DFF' : '#8A8A96';
        if (n.rot || n.flipH === true || n.flipV === true) {
          c.save(); c.translate(sx, sy); c.rotate(Math.atan2(LM[1], LM[0])); c.fillText(txt, 0, -6); c.restore();
        } else {
          c.fillText(txt, sx, sy - 6);
          labelRects.push({id: ks[i], x: sx, y: sy - 19, w: c.measureText(txt).width, h: 17});
        }
      }
    }
    if (api.showGrids !== false && pn) drawGrids(c, page, bs, tx, ty);
    if (last.dbg) { c.setTransform(1, 0, 0, 1, 0, 0); c.strokeStyle = 'rgba(255,0,80,0.8)'; c.lineWidth = 1; for (let i = 0; i < last.dbg.length; i += 4) c.strokeRect(last.dbg[i] + 0.5, last.dbg[i + 1] + 0.5, last.dbg[i + 2] - last.dbg[i] - 1, last.dbg[i + 3] - last.dbg[i + 1] - 1); c.setTransform(dpr, 0, 0, dpr, 0, 0); }
    for (let i = 0; i < overlays.length; i++) {
      c.save();
      try { overlays[i](c, view); } catch (e) { if (window.console) console.error('[HD.render] overlay', e); }
      c.restore();
      c.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
  }

  /* ------------------------------------------------------------------ view */
  function clampZoom(z) { return Math.max(0.01, Math.min(256, num(+z, 1) || 1)); }
  function setView(v, animate) {
    if (!v) return;
    const z = clampZoom(v.zoom === undefined ? view.zoom : v.zoom), x = num(+v.x, view.x), y = num(+v.y, view.y);
    if (animate && canvas && cssW > 0) {
      const cx0 = (cssW / 2 - view.x) / view.zoom, cy0 = (cssH / 2 - view.y) / view.zoom, cx1 = (cssW / 2 - x) / z, cy1 = (cssH / 2 - y) / z;
      anim = {t0: now(), dur: typeof animate === 'number' ? animate : 170, lz0: Math.log(view.zoom), lz1: Math.log(z), z1: z, cx0, cy0, cx1, cy1, x1: x, y1: y};
    } else { anim = null; view.zoom = z; view.x = snap(x); view.y = snap(y); }
    schedule();
  }
  function boundsOf(ids) {
    const s = S();
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const id of ids) {
      const n = s.get(id);
      if (!n) continue;
      if (n.type === 'PAGE') { const r = derive(id, n); if (r.x1 > r.x0) { x0 = Math.min(x0, r.x0); y0 = Math.min(y0, r.y0); x1 = Math.max(x1, r.x1); y1 = Math.max(y1, r.y1); } continue; }
      const m = worldMat(id);
      boxUnder(m[0], m[1], m[2], m[3], m[4], m[5], 0, 0, W(n), H(n));
      x0 = Math.min(x0, BX[0]); y0 = Math.min(y0, BX[1]); x1 = Math.max(x1, BX[2]); y1 = Math.max(y1, BX[3]);
    }
    return x0 === Infinity ? null : {x: x0, y: y0, w: x1 - x0, h: y1 - y0};
  }
  function zoomToFit(ids, animate) {
    if (canvas) { cssW = Math.max(1, canvas.clientWidth || cssW); cssH = Math.max(1, canvas.clientHeight || cssH); }
    const page = HD.sel && HD.sel.page;
    const list = ids && ids.length ? (Array.isArray(ids) ? ids : Array.from(ids)) : (page ? [page] : []);
    const b = boundsOf(list);
    if (!b || !(cssW > 0)) { setView({x: 0, y: 0, zoom: 1}, false); return; }
    const pad = Math.min(64, cssW * 0.08, cssH * 0.08);
    let z = Math.min((cssW - 2 * pad) / Math.max(b.w, 1), (cssH - 2 * pad) / Math.max(b.h, 1));
    z = clampZoom(Math.min(z, ids && ids.length ? 16 : 1));
    setView({zoom: z, x: cssW / 2 - (b.x + b.w / 2) * z, y: cssH / 2 - (b.y + b.h / 2) * z}, animate === undefined ? last.valid : animate);
  }
  function screenToWorld(sx, sy) { return [(sx - view.x) / view.zoom, (sy - view.y) / view.zoom]; }
  function worldToScreen(wx, wy) { return [wx * view.zoom + view.x, wy * view.zoom + view.y]; }

  /* ------------------------------------------------------------------ hit testing (real geometry) */
  let hc = null;
  function hctx() { if (!hc) { const c = document.createElement('canvas'); c.width = c.height = 2; hc = c.getContext('2d'); } return hc; }
  function inGeom(g, w, h, x, y, grow) {
    switch (g.k) {
      case R_RECT: return x >= -grow && x <= w + grow && y >= -grow && y <= h + grow;
      case R_RR: {
        if (!(x >= -grow && x <= w + grow && y >= -grow && y <= h + grow)) return false;
        const r = g.r;
        for (let i = 0; i < 4; i++) {
          const rr = r[i];
          if (rr <= 0) continue;
          const cx = i === 0 || i === 3 ? rr : w - rr, cy = i < 2 ? rr : h - rr;
          const inX = i === 0 || i === 3 ? x < cx : x > cx, inY = i < 2 ? y < cy : y > cy;
          if (inX && inY) { const d = Math.hypot(x - cx, y - cy); return d <= Math.max(0, rr + grow); }
        }
        return true;
      }
      case R_ELL: { const rx = w / 2 + grow, ry = h / 2 + grow; if (rx <= 0 || ry <= 0) return false; const u = (x - w / 2) / rx, v = (y - h / 2) / ry; return u * u + v * v <= 1; }
      case R_PATH: return hctx().isPointInPath(g.p, x, y, g.rule);
      default: return false;
    }
  }
  function nearOutline(g, w, h, x, y, d) {
    if (g.k === R_PATH) { const c = hctx(); c.lineWidth = Math.max(0.01, d * 2); return c.isPointInStroke(g.p, x, y); }
    return inGeom(g, w, h, x, y, d) && !inGeom(g, w, h, x, y, -d);
  }
  function hitShape(n, type, w, h, x, y, tol, id, v, rec) {
    if (type === 'TEXT') return x >= -tol && x <= w + tol && y >= -tol && y <= h + tol;
    const sw = anyVis(L.paints(n, 'strokes')) ? Math.max(0, num(+G(n, 'strokeWeight'), 1)) : 0;
    if (type === 'LINE') return x >= -tol && x <= w + tol && Math.abs(y) <= Math.max(sw / 2, tol);
    const g = geomOf(n, type, w, h, id, v, rec);
    const filled = anyVis(L.paints(n, 'fills'));
    if (filled && inGeom(g, w, h, x, y, 0)) return true;
    if (!filled || sw > 0) return nearOutline(g, w, h, x, y, Math.max(G(n, 'strokeAlign') === 'center' ? sw / 2 : sw, tol));
    return false;
  }
  function toLocal(n, px, py, out) {
    if (!n.rot && n.flipH !== true && n.flipV !== true) { out[0] = px - num(n.x, 0); out[1] = py - num(n.y, 0); return; }
    const m = inv(localMat(n, [1, 0, 0, 1, 0, 0]));
    out[0] = m[0] * px + m[2] * py + m[4]; out[1] = m[1] * px + m[3] * py + m[5];
  }
  function hitKids(pid, v, x, y, tol, withLocked) {
    const s = S(), ks = v !== null ? v.kids : s.children(pid);
    let maskAt = -1;
    for (let i = 0; i < ks.length; i++) { const kn = v !== null ? ks[i].n : s.get(ks[i]); if (kn && kn.mask === true && kn.visible !== false) { maskAt = i; } }
    const P = [0, 0];
    for (let i = ks.length - 1; i >= 0; i--) {
      const kv = v !== null ? ks[i] : null, kn = v !== null ? kv.n : s.get(ks[i]), kid = v !== null ? kv.key : ks[i];
      if (!kn) continue;
      if (maskAt >= 0 && i > maskAt) {
        /* behind a mask: only where the nearest mask below it covers */
        let j = i - 1;
        for (; j >= 0; j--) { const mn = v !== null ? ks[j].n : s.get(ks[j]); if (mn && mn.mask === true && mn.visible !== false) break; }
        if (j >= 0) {
          const mn = v !== null ? ks[j].n : s.get(ks[j]), mw = W(mn), mh = H(mn);
          toLocal(mn, x, y, P);
          if (!(GEO_MASK[mn.type] === 1 ? inGeom(geomOf(mn, mn.type, mw, mh), mw, mh, P[0], P[1], 0) : (P[0] >= 0 && P[1] >= 0 && P[0] <= mw && P[1] <= mh))) continue;
        }
      }
      const hit = hitNode(kn, kid, kv, x, y, tol, withLocked);
      if (hit !== null) return hit;
    }
    return null;
  }
  function hitNode(n, id, v, px, py, tol, withLocked) {
    if (n.visible === false || (!withLocked && G(n, 'locked') === true)) return null;
    const P = [0, 0];
    toLocal(n, px, py, P);
    const x = P[0], y = P[1], type = n.type === 'GROUP' ? dtype(n) : n.type, w = W(n), h = H(n);
    let rec = null;
    if (v === null) {
      rec = derive(id, n);
      if (x < rec.x0 - tol || x > rec.x1 + tol || y < rec.y0 - tol || y > rec.y1 + tol) return null;
    }
    const real = v === null;
    if (type === 'INSTANCE' && real) { v = instTree(id, n, rec); n = v.n; }
    if (type === 'BOOL') {
      /* a boolean is hit where its RESULT is; the part under the pointer is offered as the deeper hit */
      if (!hitShape(n, type, w, h, x, y, tol, id, v, rec)) return null;
      const k = hitKids(id, v, x, y, tol, withLocked);
      return k !== null ? k : id;
    }
    if (CONT[type] !== 1) return hitShape(n, type, w, h, x, y, tol) ? id : null;
    const g = type === 'GROUP' ? null : geomOf(n, type, w, h);
    const inBox = g === null ? true : inGeom(g, w, h, x, y, 0);
    if (g !== null && clips(n) && !inBox) return nearOutline(g, w, h, x, y, tol) && anyVis(L.paints(n, 'strokes')) ? id : null;
    const has = v !== null ? v.kids.length > 0 : S().children(id).length > 0;
    if (has) {
      const k = v !== null && (v.sx !== 1 || v.sy !== 1) ? hitKids(id, v, x / (v.sx || 1), y / (v.sy || 1), tol, withLocked) : hitKids(id, v, x, y, tol, withLocked);
      if (k !== null) return type === 'INSTANCE' ? id : k;
    }
    if (g === null) return null;
    if (inBox && anyVis(L.paints(n, 'fills'))) return id;
    if (anyVis(L.paints(n, 'strokes')) && nearOutline(g, w, h, x, y, Math.max(num(+G(n, 'strokeWeight'), 1), tol))) return id;
    return null;
  }
  function chainOf(id) {
    const s = S(), out = [];
    let c = id, g = 0;
    while (c && g++ < 2000) { const n = s.get(c); if (!n || n.type === 'PAGE' || n.type === 'DOCUMENT') break; out.unshift(c); c = n.parent; }
    return out;
  }
  function hitLeaf(wx, wy, opts) {
    const s = S(), page = HD.sel && HD.sel.page;
    if (!s || !page || !s.has(page)) return null;
    const tol = (opts && typeof opts.tol === 'number' ? opts.tol : 4) / (view.zoom || 1);
    const leaf = hitKids(page, null, wx, wy, tol, !!(opts && opts.locked));
    if (leaf !== null) return leaf;
    if (opts && opts.labels === false) return null;
    const sp = worldToScreen(wx, wy);
    for (let i = labelRects.length - 1; i >= 0; i--) { const r = labelRects[i]; if (sp[0] >= r.x && sp[0] <= r.x + r.w && sp[1] >= r.y && sp[1] <= r.y + r.h && s.has(r.id) && (opts && opts.locked || G(s.get(r.id), 'locked') !== true)) return r.id; }
    return null;
  }
  function hitTest(wx, wy, opts) {
    const leaf = hitLeaf(wx, wy, opts);
    if (leaf === null || (opts && opts.deep)) return leaf;
    const ch = chainOf(leaf);
    if (!ch.length) return null;
    const top = S().get(ch[0]);
    return ch.length > 1 && top && TOPC[top.type] === 1 ? ch[1] : ch[0];
  }
  function hitChain(wx, wy, opts) { const leaf = hitLeaf(wx, wy, opts); return leaf === null ? [] : chainOf(leaf); }
  /* does the box (0,0,w,h) under m touch the rect? (separating axes: exact for turned boxes) */
  function boxHitsRect(m, w, h, r) {
    boxUnder(m[0], m[1], m[2], m[3], m[4], m[5], 0, 0, w, h);
    if (BX[2] < r.x || BX[0] > r.x + r.w || BX[3] < r.y || BX[1] > r.y + r.h) return false;
    if (m[1] === 0 && m[2] === 0) return true;
    const im = inv(m), cs = [[r.x, r.y], [r.x + r.w, r.y], [r.x + r.w, r.y + r.h], [r.x, r.y + r.h]];
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const c of cs) { const x = im[0] * c[0] + im[2] * c[1] + im[4], y = im[1] * c[0] + im[3] * c[1] + im[5]; x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
    return !(x1 < 0 || x0 > w || y1 < 0 || y0 > h);
  }
  function nodesInRect(rect, pageId) {
    const s = S(), out = [];
    const page = pageId || (HD.sel && HD.sel.page);
    if (!s || !page || !rect) return out;
    const r = {x: rect.w < 0 ? rect.x + rect.w : rect.x, y: rect.h < 0 ? rect.y + rect.h : rect.y, w: Math.abs(rect.w), h: Math.abs(rect.h)};
    const ok = (n) => n && n.visible !== false && G(n, 'locked') !== true;
    const ks = s.children(page);
    for (let i = 0; i < ks.length; i++) {
      const n = s.get(ks[i]);
      if (!ok(n)) continue;
      const m = localMat(n, [1, 0, 0, 1, 0, 0]), w = W(n), h = H(n);
      if (!boxHitsRect(m, w, h, r)) {
        /* a frame that does not clip can still show children outside its own box */
        if (TOPC[n.type] !== 1 || clips(n)) continue;
      }
      const kids = TOPC[n.type] === 1 ? s.children(ks[i]) : EMPTY;
      if (kids.length) {
        boxUnder(m[0], m[1], m[2], m[3], m[4], m[5], 0, 0, w, h);
        if (BX[0] >= r.x && BX[1] >= r.y && BX[2] <= r.x + r.w && BX[3] <= r.y + r.h) { out.push(ks[i]); continue; }
        for (let j = 0; j < kids.length; j++) {
          const c = s.get(kids[j]);
          if (!ok(c)) continue;
          if (boxHitsRect(mul(m, localMat(c, [1, 0, 0, 1, 0, 0])), W(c), H(c), r)) out.push(kids[j]);
        }
      } else if (boxHitsRect(m, w, h, r)) out.push(ks[i]);
    }
    return out;
  }

  /* ------------------------------------------------------------------ export: canvas */
  function exactT(ctx, w, h, scale) {
    return {ctx, clips: null, bounds: [0, 0, w, h], lod: false, cache: false, canBuild: false, record: false, exact: true,
      bs: scale, btx: 0, bty: 0, serial: ++serial, budgetEnd: 0, now: now(), root: null, inexact: false, backdrop: true};
  }
  /* the box a node takes when exported: {x, y, w, h} in its parent's space (a page: around everything on it) */
  function exportBounds(id, mode) {
    const s = S(), n = s.get(id);
    if (!n) return null;
    const r = derive(id, n);
    if (n.type === 'PAGE') return {x: r.x0, y: r.y0, w: Math.max(0, r.x1 - r.x0), h: Math.max(0, r.y1 - r.y0)};
    localMat(n, LM);
    if (mode === 'box') boxUnder(LM[0], LM[1], LM[2], LM[3], LM[4], LM[5], 0, 0, W(n), H(n));
    else boxUnder(LM[0], LM[1], LM[2], LM[3], LM[4], LM[5], r.x0, r.y0, r.x1, r.y1);
    return {x: BX[0], y: BX[1], w: BX[2] - BX[0], h: BX[3] - BX[1]};
  }
  /* toCanvas(id, scale, {bg, bounds:'paint'|'box'}) -> a fresh canvas with the node drawn exactly (no culling, no LOD, no caches) */
  function toCanvas(id, scale, opts) {
    const s = S(), n = s && s.get(id);
    scale = Math.max(0.01, num(+scale, 1));
    const cv = document.createElement('canvas');
    if (!n) { cv.width = cv.height = 1; return cv; }
    const b = exportBounds(id, opts && opts.bounds) || {x: 0, y: 0, w: 1, h: 1};
    let cw = Math.max(1, Math.ceil(b.w * scale - 0.001)), ch = Math.max(1, Math.ceil(b.h * scale - 0.001));
    const k = Math.min(1, 16384 / cw, 16384 / ch, Math.sqrt(1.2e8 / (cw * ch)));
    if (k < 1) { scale *= k; cw = Math.max(1, Math.floor(cw * k)); ch = Math.max(1, Math.floor(ch * k)); }
    cv.width = cw; cv.height = ch;
    const ctx = cv.getContext('2d');
    let bg = opts && opts.bg;
    if (bg === undefined && n.type === 'PAGE') bg = G(n, 'bg') || '#F5F5F5';
    if (typeof bg === 'string' && bg && bg !== 'transparent') { ctx.fillStyle = bg; ctx.fillRect(0, 0, cw, ch); }
    const T = exactT(ctx, cw, ch, scale), saveLD = LD, saveEd = editingId;
    editingId = null;
    try {
      if (n.type === 'PAGE') paintKidsFrom(T, id, null, 0, scale, 0, 0, scale, -b.x * scale, -b.y * scale);
      else paintNode(T, n, id, null, scale, 0, 0, scale, -b.x * scale, -b.y * scale);
    } finally { LD = saveLD; editingId = saveEd; }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    cv.hdScale = scale;
    return cv;
  }
  /* drawNode(ctx, id, {world}) - the node drawn into any 2D context. Default: its box sits at the context's origin
     (its own x / y / rotation are left out); {world: true}: it is drawn where it lies on the page. */
  function drawNode(ctx, id, opts) {
    const s = S(), n = s && s.get(id);
    if (!n || !ctx) return;
    let m0 = [1, 0, 0, 1, 0, 0];
    try { const t = ctx.getTransform(); m0 = [t.a, t.b, t.c, t.d, t.e, t.f]; } catch (e) { /* identity */ }
    const cvs = ctx.canvas || {width: 1e5, height: 1e5};
    const T = exactT(ctx, cvs.width, cvs.height, Math.sqrt(Math.abs(m0[0] * m0[3] - m0[1] * m0[2])) || 1), saveLD = LD;
    ctx.save();
    try {
      if (n.type === 'PAGE') paintKidsFrom(T, id, null, 0, m0[0], m0[1], m0[2], m0[3], m0[4], m0[5]);
      else {
        const pm = opts && opts.world ? mul(m0, worldMat(n.parent)) : mul(m0, inv(localMat(n, [1, 0, 0, 1, 0, 0])));
        paintNode(T, n, id, null, pm[0], pm[1], pm[2], pm[3], pm[4], pm[5]);
      }
    } finally { LD = saveLD; ctx.restore(); }
  }
  /* ready(id) -> Promise: every image and font the subtree needs has arrived (or failed) - await it before an export */
  function ready(id, ms) {
    const s = S();
    const scan = () => {
      let waiting = 0;
      const seen = new Set();
      const look = (n) => {
        if (!n) return;
        for (const key of ['fills', 'strokes']) { const a = L.paints(n, key); for (const p of a) if (p && p.type === 'image' && p.hash) { image(p.hash); const e = imgs.get(p.hash); if (e && e.st === 'load') waiting++; } }
        if (n.type === 'TEXT') { const tl = L.textLayout(n); for (const ln of tl.lines) for (const sg of ln.segs) { if (!famReady(sg.st.font)) { needFont(sg.st); if (!famReady(sg.st.font)) waiting++; } } }
        if (n.type === 'INSTANCE' && n.comp && !seen.has(n.comp)) { seen.add(n.comp); walk(n.comp); }
      };
      const walk = (nid) => { let g = 0; const st = [nid]; while (st.length && g++ < 300000) { const c = st.pop(), n = s.get(c); if (!n) continue; look(n); const ks = s.children(c); for (let i = 0; i < ks.length; i++) st.push(ks[i]); } };
      walk(id);
      return waiting;
    };
    return new Promise((res) => {
      const t0 = now(), lim = ms || 6000;
      (function poll() { const w = scan(); if (!w || now() - t0 > lim) res(!w); else setTimeout(poll, 80); })();
    });
  }

  /* ------------------------------------------------------------------ export: SVG */
  function esc(v) { return String(v).replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\uFFFE\uFFFF]/g, '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
  function fnum(v) { v = Math.round(num(+v, 0) * 1000) / 1000; return Object.is(v, -0) ? '0' : String(v); }
  function fnum6(v) { v = Math.round(num(+v, 0) * 1e6) / 1e6; return Object.is(v, -0) ? '0' : String(v); }
  function hex6(color) {
    if (typeof color !== 'string' || color[0] !== '#') return ['#000000', 1];
    let h = color.slice(1);
    if (h.length === 3 || h.length === 4) h = h.split('').map(c => c + c).join('');
    if (!/^[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(h)) return ['#000000', 1];
    return ['#' + h.slice(0, 6), h.length === 8 ? parseInt(h.slice(6), 16) / 255 : 1];
  }
  function rrPath(x, y, w, h, r) {
    const a = r[0], b = r[1], c = r[2], d = r[3], f = fnum;
    return 'M' + f(x + a) + ' ' + f(y) + 'H' + f(x + w - b) + (b ? 'A' + f(b) + ' ' + f(b) + ' 0 0 1 ' + f(x + w) + ' ' + f(y + b) : '') + 'V' + f(y + h - c) +
      (c ? 'A' + f(c) + ' ' + f(c) + ' 0 0 1 ' + f(x + w - c) + ' ' + f(y + h) : '') + 'H' + f(x + d) + (d ? 'A' + f(d) + ' ' + f(d) + ' 0 0 1 ' + f(x) + ' ' + f(y + h - d) : '') +
      'V' + f(y + a) + (a ? 'A' + f(a) + ' ' + f(a) + ' 0 0 1 ' + f(x + a) + ' ' + f(y) : '') + 'Z';
  }
  function toSVG(id, opts) {
    const s = S(), n0 = s && s.get(id);
    if (!n0) return '';
    const defs = [];
    let uid = 0;
    const nid = (p) => 'hd' + p + (++uid);
    const boolD = new Map();               /* a boolean group -> the path data of its result */
    const dataURLs = new Map();
    const dataURL = (hash) => {
      if (dataURLs.has(hash)) return dataURLs.get(hash);
      let u = null;
      const im = image(hash);
      if (im && (im.naturalWidth || im.width)) {
        try { const c = document.createElement('canvas'); c.width = im.naturalWidth || im.width; c.height = im.naturalHeight || im.height; c.getContext('2d').drawImage(im, 0, 0); u = c.toDataURL('image/png'); } catch (e) { u = null; }
      }
      dataURLs.set(hash, u);
      return u;
    };
    /* the outline of a node as one SVG element (grown by `grow`), with extra attributes */
    function shape(n, type, w, h, grow, attrs) {
      if (type === 'ELLIPSE') return '<ellipse cx="' + fnum(w / 2) + '" cy="' + fnum(h / 2) + '" rx="' + fnum(Math.max(0, w / 2 + grow)) + '" ry="' + fnum(Math.max(0, h / 2 + grow)) + '"' + attrs + '/>';
      if (type === 'LINE') return '<line x1="0" y1="0" x2="' + fnum(w) + '" y2="0"' + attrs + '/>';
      if (type === 'BOOL') return '<path d="' + (boolD.get(n) || 'M0 0') + '"' + attrs + '/>';
      if (type === 'VECTOR') {
        const out = segsToD(vectorSegs(n));
        return '<path d="' + out + '"' + (n.fillRule === 'evenodd' ? ' fill-rule="evenodd"' : '') + attrs + '/>';
      }
      if (type === 'POLYGON' || type === 'STAR') {
        const pts = polyPoints(G(n, 'sides'), type === 'STAR' ? G(n, 'ratio') : 1, type === 'STAR');
        let d = '';
        for (let i = 0; i < pts.length; i += 2) d += (i ? 'L' : 'M') + fnum(pts[i] * w) + ' ' + fnum(pts[i + 1] * h);
        return '<path d="' + d + 'Z"' + attrs + '/>';
      }
      const r = radii(n, w, h), x = -grow, y = -grow, ww = Math.max(0, w + 2 * grow), hh = Math.max(0, h + 2 * grow);
      if (r === null) return '<rect x="' + fnum(x) + '" y="' + fnum(y) + '" width="' + fnum(ww) + '" height="' + fnum(hh) + '"' + attrs + '/>';
      const g = r.map(v => (v > 0 ? Math.max(0, Math.min(v + grow, Math.min(ww, hh) / 2)) : 0));
      if (g[0] === g[1] && g[1] === g[2] && g[2] === g[3]) return '<rect x="' + fnum(x) + '" y="' + fnum(y) + '" width="' + fnum(ww) + '" height="' + fnum(hh) + '" rx="' + fnum(g[0]) + '"' + attrs + '/>';
      return '<path d="' + rrPath(x, y, ww, hh, g) + '"' + attrs + '/>';
    }
    /* a paint as SVG attributes: [paintValue, opacity] */
    function paintRef(p, w, h) {
      const po = p.opacity === undefined ? 1 : p.opacity;
      if (p.type === 'solid' || p.type === undefined) { const c = hex6(p.color); return [c[0], c[1] * po]; }
      const stops = Array.isArray(p.stops) && p.stops.length ? p.stops : [{pos: 0, color: '#000000'}, {pos: 1, color: '#FFFFFF'}];
      const lin = p.type === 'linear';
      const f = Array.isArray(p.from) ? p.from : (lin ? [0.5, 0] : [0.5, 0.5]), t = Array.isArray(p.to) ? p.to : (lin ? [0.5, 1] : [1, 0.5]);
      if (p.type === 'angular') {
        /* SVG has no sweep gradient: it is painted into a picture (up to 1024 px a side) and used as a pattern over the
           box. Close, not exact: it softens when zoomed far in, and a stroke outside the box takes the nearest edge colour. */
        let u = null;
        if (HAS_CONIC && w > EPS && h > EPS) {
          try {
            const k = Math.min(4, 1024 / Math.max(w, h)), cv = document.createElement('canvas');
            cv.width = Math.max(2, Math.round(w * k)); cv.height = Math.max(2, Math.round(h * k));
            const cx = cv.getContext('2d'), fx0 = num(+f[0], 0.5), fy0 = num(+f[1], 0.5), tx0 = num(+t[0], 1), ty0 = num(+t[1], 0.5);
            cx.scale(cv.width, cv.height);
            const g = unitGrad(p, w, h) ? cx.createConicGradient(Math.atan2(ty0 - fy0, tx0 - fx0), fx0, fy0) : cx.createConicGradient(Math.atan2((ty0 - fy0) * h, (tx0 - fx0) * w), fx0, fy0);
            for (const sp of stops) if (sp) g.addColorStop(Math.max(0, Math.min(1, num(+sp.pos, 0))), rgba(sp.color, sp.opacity));
            cx.fillStyle = g; cx.fillRect(0, 0, 1, 1);
            u = cv.toDataURL('image/png');
          } catch (e) { u = null; }
        }
        if (!u) { const c = hex6(stops[0].color); return [c[0], c[1] * po * (stops[0].opacity === undefined ? 1 : stops[0].opacity)]; }
        const pid = nid('p');
        defs.push('<pattern id="' + pid + '" patternUnits="userSpaceOnUse" x="0" y="0" width="' + fnum(w) + '" height="' + fnum(h) + '"><image href="' + esc(u) + '" x="0" y="0" width="' + fnum(w) + '" height="' + fnum(h) + '" preserveAspectRatio="none"/></pattern>');
        return ['url(#' + pid + ')', po];
      }
      const unit = unitGrad(p, w, h), uw = unit ? 1 : w, uh = unit ? 1 : h;
      const fx = num(+f[0], 0.5) * uw, fy = num(+f[1], 0) * uh, tx = num(+t[0], 0.5) * uw, ty = num(+t[1], 1) * uh;
      const gid = nid('g');
      let st = '';
      for (const sp of stops) { if (!sp) continue; const c = hex6(sp.color), o = c[1] * (sp.opacity === undefined ? 1 : sp.opacity); st += '<stop offset="' + fnum(Math.max(0, Math.min(1, num(+sp.pos, 0)))) + '" stop-color="' + c[0] + '"' + (o < 1 ? ' stop-opacity="' + fnum(o) + '"' : '') + '/>'; }
      if (lin) defs.push('<linearGradient id="' + gid + '" gradientUnits="userSpaceOnUse" x1="' + fnum(fx) + '" y1="' + fnum(fy) + '" x2="' + fnum(tx) + '" y2="' + fnum(ty) + '">' + st + '</linearGradient>');
      else if (unit) defs.push('<radialGradient id="' + gid + '" gradientUnits="userSpaceOnUse" cx="' + fnum6(fx) + '" cy="' + fnum6(fy) + '" r="' + fnum6(Math.max(1e-5, Math.hypot(tx - fx, ty - fy))) + '" gradientTransform="scale(' + fnum(w) + ' ' + fnum(h) + ')">' + st + '</radialGradient>');
      else defs.push('<radialGradient id="' + gid + '" gradientUnits="userSpaceOnUse" cx="' + fnum(fx) + '" cy="' + fnum(fy) + '" r="' + fnum(Math.max(0.01, Math.hypot(tx - fx, ty - fy))) + '">' + st + '</radialGradient>');
      return ['url(#' + gid + ')', po];
    }
    function fillsOf(n, type, w, h) {
      const fills = L.paints(n, 'fills');
      let out = '';
      for (const p of fills) {
        if (!vis(p)) continue;
        if (p.type === 'image') {
          const po = p.opacity === undefined ? 1 : p.opacity, u = dataURL(p.hash);
          if (!u) { out += shape(n, type, w, h, 0, ' fill="#E3E3E8"' + (po < 1 ? ' fill-opacity="' + fnum(po) + '"' : '')); continue; }
          const cid = nid('c');
          defs.push('<clipPath id="' + cid + '">' + shape(n, type, w, h, 0, '') + '</clipPath>');
          if (p.mode === 'tile') {
            const im = image(p.hash), pid = nid('p'), sc = num(+p.scale, 1), iw = (im.naturalWidth || im.width) * sc, ih = (im.naturalHeight || im.height) * sc;
            defs.push('<pattern id="' + pid + '" patternUnits="userSpaceOnUse" width="' + fnum(iw) + '" height="' + fnum(ih) + '"><image href="' + esc(u) + '" width="' + fnum(iw) + '" height="' + fnum(ih) + '"/></pattern>');
            out += shape(n, type, w, h, 0, ' fill="url(#' + pid + ')"' + (po < 1 ? ' fill-opacity="' + fnum(po) + '"' : ''));
          } else if (p.mode === 'crop' && Array.isArray(p.crop) && p.crop.length === 4) {
            const im = image(p.hash), iw = im.naturalWidth || im.width, ih = im.naturalHeight || im.height;
            const sx = Math.max(0, Math.min(1, +p.crop[0] || 0)) * iw, sy = Math.max(0, Math.min(1, +p.crop[1] || 0)) * ih;
            const sw = Math.max(1, Math.min(iw - sx, (+p.crop[2] || 1) * iw)), sh = Math.max(1, Math.min(ih - sy, (+p.crop[3] || 1) * ih));
            out += '<g clip-path="url(#' + cid + ')"' + (po < 1 ? ' opacity="' + fnum(po) + '"' : '') + '><svg x="0" y="0" width="' + fnum(w) + '" height="' + fnum(h) + '" viewBox="' + fnum(sx) + ' ' + fnum(sy) + ' ' + fnum(sw) + ' ' + fnum(sh) + '" preserveAspectRatio="xMidYMid slice"><image href="' + esc(u) + '" width="' + fnum(iw) + '" height="' + fnum(ih) + '"/></svg></g>';
          } else out += '<g clip-path="url(#' + cid + ')"><image href="' + esc(u) + '" x="0" y="0" width="' + fnum(w) + '" height="' + fnum(h) + '" preserveAspectRatio="xMidYMid ' + (p.mode === 'fit' ? 'meet' : 'slice') + '"' + (po < 1 ? ' opacity="' + fnum(po) + '"' : '') + '/></g>';
          continue;
        }
        const r = paintRef(p, w, h);
        out += shape(n, type, w, h, 0, ' fill="' + r[0] + '"' + (r[1] < 1 ? ' fill-opacity="' + fnum(r[1]) + '"' : ''));
      }
      return out;
    }
    function strokeAttrs(n, r, sw) {
      const dash = G(n, 'dash'), cap = G(n, 'strokeCap') || 'butt', join = G(n, 'strokeJoin') || 'miter';
      return ' fill="none" stroke="' + r[0] + '"' + (r[1] < 1 ? ' stroke-opacity="' + fnum(r[1]) + '"' : '') + ' stroke-width="' + fnum(sw) + '"' +
        (cap !== 'butt' ? ' stroke-linecap="' + esc(cap) + '"' : '') + (join !== 'miter' ? ' stroke-linejoin="' + esc(join) + '"' : ' stroke-miterlimit="4"') +
        (Array.isArray(dash) && dash.length ? ' stroke-dasharray="' + dash.map(fnum).join(' ') + '"' : '');
    }
    function strokesOf(n, type, w, h) {
      const strokes = L.paints(n, 'strokes'), sw = num(+G(n, 'strokeWeight'), 1);
      if (!(sw > 0) || !strokes.length) return '';
      let align = G(n, 'strokeAlign') || 'center';
      const pathy = type === 'VECTOR' || type === 'POLYGON' || type === 'STAR' || type === 'BOOL';
      if (type === 'LINE' || (type === 'VECTOR' && !pathBBox(typeof n.path === 'string' ? n.path : '').closed)) align = 'center';
      let out = '';
      for (const p of strokes) {
        if (!vis(p)) continue;
        const r = p.type === 'image' ? ['#D8D8DC', p.opacity === undefined ? 1 : p.opacity] : paintRef(p, w, h);
        if (align === 'center') out += shape(n, type, w, h, 0, strokeAttrs(n, r, sw));
        else if (!pathy) out += shape(n, type, w, h, align === 'inside' ? -sw / 2 : sw / 2, strokeAttrs(n, r, sw));
        else if (align === 'inside') { const cid = nid('c'); defs.push('<clipPath id="' + cid + '">' + shape(n, type, w, h, 0, '') + '</clipPath>'); out += shape(n, type, w, h, 0, strokeAttrs(n, r, sw * 2) + ' clip-path="url(#' + cid + ')"'); }
        else { const mid = nid('m'), m = sw * 2 + 4; defs.push('<mask id="' + mid + '" maskUnits="userSpaceOnUse" x="' + fnum(-m) + '" y="' + fnum(-m) + '" width="' + fnum(w + 2 * m) + '" height="' + fnum(h + 2 * m) + '"><rect x="' + fnum(-m) + '" y="' + fnum(-m) + '" width="' + fnum(w + 2 * m) + '" height="' + fnum(h + 2 * m) + '" fill="#fff"/>' + shape(n, type, w, h, 0, ' fill="#000"') + '</mask>'); out += shape(n, type, w, h, 0, strokeAttrs(n, r, sw * 2) + ' mask="url(#' + mid + ')"'); }
      }
      return out;
    }
    function textOf(n, w, h) {
      const lay = L.textLayout(n), fills = L.paints(n, 'fills');
      let fill = ['none', 1];
      for (const p of fills) if (vis(p)) fill = p.type === 'image' ? ['#888888', 1] : paintRef(p, w, h);
      const strokes = L.paints(n, 'strokes'), sw = num(+G(n, 'strokeWeight'), 1), align = G(n, 'strokeAlign') || 'center';
      const spans = (own) => {
        let t = '';
        for (const ln of lay.lines) for (const sg of ln.segs) {
          if (sg.sp && sg.st.deco === 'none') continue;
          const st = sg.st;
          let a = ' x="' + fnum(sg.x) + '" y="' + fnum(ln.base) + '" font-family="' + esc(st.font) + ', Inter, sans-serif" font-size="' + fnum(st.size) + '" font-weight="' + st.weight + '"';
          if (st.italic) a += ' font-style="italic"';
          if (st.ls) a += ' letter-spacing="' + fnum(st.ls) + '"';
          if (st.deco === 'underline') a += ' text-decoration="underline"'; else if (st.deco === 'strike') a += ' text-decoration="line-through"';
          if (own && Array.isArray(st.fills)) for (const p of st.fills) if (vis(p) && p.type !== 'image') { const r = paintRef(p, w, h); a += ' fill="' + r[0] + '"' + (r[1] < 1 ? ' fill-opacity="' + fnum(r[1]) + '"' : ''); }
          t += '<tspan' + a + '>' + esc(sg.text) + '</tspan>';
        }
        return t;
      };
      const bare = spans(false);
      let out = '<text xml:space="preserve" fill="' + fill[0] + '"' + (fill[1] < 1 ? ' fill-opacity="' + fnum(fill[1]) + '"' : '') + '>' + spans(true) + '</text>';
      /* strokes as their own text on top: centre = as wide as asked; inside / outside = twice as wide, cut by the letters */
      let cut = '';
      for (const p of strokes) {
        if (!vis(p) || !(sw > 0) || p.type === 'image') continue;
        const r = paintRef(p, w, h);
        if (align !== 'center' && !cut) {
          if (align === 'inside') { const cid = nid('c'); defs.push('<clipPath id="' + cid + '"><text xml:space="preserve">' + bare + '</text></clipPath>'); cut = ' clip-path="url(#' + cid + ')"'; }
          else { const mid = nid('m'), o = sw * 2 + num(+G(n, 'fontSize'), 16); defs.push('<mask id="' + mid + '" maskUnits="userSpaceOnUse" x="' + fnum(-o) + '" y="' + fnum(-o) + '" width="' + fnum(Math.max(w, lay.cw) + 2 * o) + '" height="' + fnum(Math.max(h, lay.ch) + 2 * o) + '"><rect x="' + fnum(-o) + '" y="' + fnum(-o) + '" width="' + fnum(Math.max(w, lay.cw) + 2 * o) + '" height="' + fnum(Math.max(h, lay.ch) + 2 * o) + '" fill="#fff"/><text xml:space="preserve" fill="#000">' + bare + '</text></mask>'); cut = ' mask="url(#' + mid + ')"'; }
        }
        out += '<text xml:space="preserve" fill="none" stroke="' + r[0] + '"' + (r[1] < 1 ? ' stroke-opacity="' + fnum(r[1]) + '"' : '') + ' stroke-width="' + fnum(align === 'center' ? sw : sw * 2) + '" stroke-linejoin="' + (G(n, 'strokeJoin') === 'miter' ? 'miter' : 'round') + '"' + cut + '>' + bare + '</text>';
      }
      return out;
    }
    function filterOf(fx, box) {
      const fid = nid('f');
      let body = '', merge = '', after = '', k = 0, blur = 0, grow = 0;
      for (const e of fx) if (e.type === 'inner') grow = Math.max(grow, Math.abs(num(+e.x, 0)) + Math.abs(num(+e.y, 0)) + num(+e.blur, 0) * 2 + Math.abs(num(+e.spread, 0)) + 4);
      box = [box[0] - grow, box[1] - grow, box[2] + grow, box[3] + grow];
      for (const e of fx) {
        const c = hex6(e.color || '#000000'), o = c[1] * (e.opacity === undefined ? 0.25 : e.opacity), sd = fnum(Math.max(0, num(+e.blur, 0)) / 2), sp = num(+e.spread, 0);
        if (e.type === 'drop') {
          const r = 'd' + (++k);
          body += (sp !== 0 ? '<feMorphology in="SourceAlpha" operator="' + (sp > 0 ? 'dilate' : 'erode') + '" radius="' + fnum(Math.abs(sp)) + '" result="' + r + 'm"/>' : '') +
            '<feGaussianBlur in="' + (sp !== 0 ? r + 'm' : 'SourceAlpha') + '" stdDeviation="' + sd + '" result="' + r + 'b"/><feOffset in="' + r + 'b" dx="' + fnum(e.x) + '" dy="' + fnum(e.y) + '" result="' + r + 'o"/>' +
            '<feFlood flood-color="' + c[0] + '" flood-opacity="' + fnum(o) + '" result="' + r + 'f"/><feComposite in="' + r + 'f" in2="' + r + 'o" operator="in" result="' + r + '"/>';
          merge += '<feMergeNode in="' + r + '"/>';
        } else if (e.type === 'inner') {
          const r = 'i' + (++k);
          body += '<feFlood flood-color="' + c[0] + '" flood-opacity="' + fnum(o) + '" result="' + r + 'f"/><feComposite in="' + r + 'f" in2="SourceAlpha" operator="out" result="' + r + 'v"/>' +
            '<feGaussianBlur in="' + r + 'v" stdDeviation="' + sd + '" result="' + r + 'b"/><feOffset in="' + r + 'b" dx="' + fnum(e.x) + '" dy="' + fnum(e.y) + '" result="' + r + 'o"/>' +
            '<feComposite in="' + r + 'o" in2="SourceAlpha" operator="in" result="' + r + '"/>';
          after += '<feMergeNode in="' + r + '"/>';
        } else if (e.type === 'blur') blur = Math.max(blur, num(+e.blur, 0));
      }
      body += '<feMerge result="all">' + merge + '<feMergeNode in="SourceGraphic"/>' + after + '</feMerge>';
      if (blur > 0) body += '<feGaussianBlur in="all" stdDeviation="' + fnum(blur / 2) + '"/>';
      defs.push('<filter id="' + fid + '" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB" x="' + fnum(box[0]) + '" y="' + fnum(box[1]) + '" width="' + fnum(box[2] - box[0]) + '" height="' + fnum(box[3] - box[1]) + '">' + body + '</filter>');
      return fid;
    }
    function kidsOf(id, v, list) {
      let out = '';
      for (let i = 0; i < list.length; i++) {
        const kv = v !== null ? list[i] : null, kn = v !== null ? kv.n : s.get(list[i]), kid = v !== null ? kv.key : list[i];
        if (!kn || kn.visible === false) continue;
        if (kn.mask === true) {
          /* the mask covers the siblings above it, up to the next mask */
          let j = i + 1;
          for (; j < list.length; j++) { const jn = v !== null ? list[j].n : s.get(list[j]); if (jn && jn.mask === true && jn.visible !== false) break; }
          const mid = nid('m');
          let mk = Object.assign({}, kn, {mask: false});
          if (clipMask(kn) && !anyVis(L.paints(kn, 'fills'))) mk = Object.assign(mk, {fills: [{type: 'solid', color: '#000000'}]});
          defs.push('<mask id="' + mid + '" style="mask-type:alpha">' + node(mk, kid, kv) + '</mask>');
          const inner = kidsOf(id, v, list.slice(i + 1, j));
          if (inner) out += '<g mask="url(#' + mid + ')">' + inner + '</g>';
          i = j - 1;
          continue;
        }
        out += node(kn, kid, kv);
      }
      return out;
    }
    function node(n, id, v) {
      if (!n || n.visible === false) return '';
      let type = n.type === 'GROUP' ? dtype(n) : n.type;
      const real = v === null;
      let rec = null;
      if (real) rec = derive(id, n);
      if (type === 'INSTANCE' && real) { v = instTree(id, n, rec); n = v.n; }
      if (type === 'BOOL') boolD.set(n, boolGeom(n, id, v, rec).d);
      const w = W(n), h = H(n);
      const m = localMat(n, [1, 0, 0, 1, 0, 0]);
      let attrs = '';
      if (!(m[0] === 1 && m[1] === 0 && m[2] === 0 && m[3] === 1 && m[4] === 0 && m[5] === 0)) attrs += m[1] === 0 && m[2] === 0 && m[0] === 1 && m[3] === 1 ? ' transform="translate(' + fnum(m[4]) + ' ' + fnum(m[5]) + ')"' : ' transform="matrix(' + m.map(fnum).join(' ') + ')"';
      const op = num(+G(n, 'opacity'), 1);
      if (op < 1) attrs += ' opacity="' + fnum(Math.max(0, op)) + '"';
      const bl = G(n, 'blend');
      if (bl && bl !== 'normal' && bl !== 'pass' && BLEND[bl]) attrs += ' style="mix-blend-mode:' + esc(bl) + '"';
      const fx = fxList(n);
      if (fx && fx.some(e => e.type !== 'bgblur')) { const ex = real ? [rec.x0, rec.y0, rec.x1, rec.y1] : vExt(v); attrs += ' filter="url(#' + filterOf(fx, [ex[0] - 2, ex[1] - 2, ex[2] + 2, ex[3] + 2]) + ')"'; }
      let body = '';
      if (type === 'TEXT') body = textOf(n, w, h);
      else if (type === 'GROUP') body = kidsOf(id, v, v !== null ? v.kids : s.children(id));
      else {
        if (type !== 'LINE') body += fillsOf(n, type, w, h);
        if (CONT[type] === 1) {
          const list = v !== null ? v.kids : s.children(id);
          if (list.length) {
            let inner = kidsOf(id, v, list);
            if (v !== null && (v.sx !== 1 || v.sy !== 1)) inner = '<g transform="scale(' + fnum(v.sx) + ' ' + fnum(v.sy) + ')">' + inner + '</g>';
            if (clips(n)) { const cid = nid('c'); defs.push('<clipPath id="' + cid + '">' + shape(n, type, w, h, 0, '') + '</clipPath>'); inner = '<g clip-path="url(#' + cid + ')">' + inner + '</g>'; }
            body += inner;
          }
        }
        body += strokesOf(n, type, w, h);
      }
      return body ? '<g' + attrs + '>' + body + '</g>' : '';
    }
    const b = exportBounds(id, opts && opts.bounds) || {x: 0, y: 0, w: 1, h: 1};
    const bw = Math.max(1, b.w), bh = Math.max(1, b.h);
    let body;
    if (n0.type === 'PAGE') body = kidsOf(id, null, s.children(id)); else body = node(n0, id, null);
    let bg = opts && opts.bg;
    if (bg === undefined && n0.type === 'PAGE') bg = G(n0, 'bg') || '#F5F5F5';
    const bgEl = typeof bg === 'string' && bg && bg !== 'transparent' ? '<rect width="' + fnum(bw) + '" height="' + fnum(bh) + '" fill="' + esc(bg) + '"/>' : '';
    return '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="' + fnum(bw) + '" height="' + fnum(bh) + '" viewBox="0 0 ' + fnum(bw) + ' ' + fnum(bh) + '">' +
      (defs.length ? '<defs>' + defs.join('') + '</defs>' : '') + bgEl + '<g transform="translate(' + fnum(-b.x) + ' ' + fnum(-b.y) + ')">' + body + '</g></svg>';
  }

  /* ------------------------------------------------------------------ public */
  let hookedStore = null, hookedSel = null;
  function hook() {
    const s = S();
    if (s && hookedStore !== s && typeof s.on === 'function') { hookedStore = s; s.on('change', onChange); s.on('load', onLoad); }
    if (HD.sel && hookedSel !== HD.sel && typeof HD.sel.on === 'function') { hookedSel = HD.sel; HD.sel.on('change', () => { overlayDirty = true; schedule(); }); }
    L.hook();
  }
  function init(cv) {
    if (!cv || typeof cv.getContext !== 'function') throw new Error('HD.render.init needs a <canvas>');
    if (canvas === cv) { resize(); return api; }
    if (ro) { try { ro.disconnect(); } catch (e) { /* gone */ } ro = null; }
    canvas = cv;
    vctx = cv.getContext('2d', {alpha: false}) || cv.getContext('2d');
    scene = document.createElement('canvas');
    sctx = scene.getContext('2d', {alpha: false}) || scene.getContext('2d');
    /* a canvas sized only by its width / height attributes would grow with every backing-store change: pin it to its box */
    const cw0 = cv.clientWidth, ch0 = cv.clientHeight;
    if (!cv.style.width && cw0 === cv.width && ch0 === cv.height) { const cs = getComputedStyle(cv); if (cs.position !== 'absolute' && cs.position !== 'fixed' && !/%/.test(cs.width)) { cv.style.width = '100%'; cv.style.height = '100%'; if (cs.display === 'inline') cv.style.display = 'block'; } }
    last.valid = false; sceneFull = true;
    hook();
    syncSize();
    if (typeof ResizeObserver === 'function') { ro = new ResizeObserver(() => { if (syncSize()) schedule(); }); ro.observe(cv); }
    window.addEventListener('resize', resize);
    try { const mq = window.matchMedia('(resolution: ' + (window.devicePixelRatio || 1) + 'dppx)'); if (mq && mq.addEventListener) mq.addEventListener('change', resize); } catch (e) { /* old browser */ }
    schedule();
    return api;
  }
  function resize() { if (canvas && syncSize()) schedule(); else schedule(); }
  function invalidate(full) {
    if (full === true) { sceneFull = true; }
    overlayDirty = true;
    schedule();
  }
  function flush() { if (raf) { cancelAnimationFrame(raf); raf = 0; } frame(); return stats.ms; }
  function addOverlay(fn) {
    if (typeof fn !== 'function') return function () {};
    overlays.push(fn);
    schedule();
    return function () { const i = overlays.indexOf(fn); if (i >= 0) overlays.splice(i, 1); schedule(); };
  }
  function on(evt, fn) {
    if (!listeners[evt] || typeof fn !== 'function') return function () {};
    listeners[evt].push(fn);
    return function () { const i = listeners[evt].indexOf(fn); if (i >= 0) listeners[evt].splice(i, 1); };
  }
  function setEditing(id) {
    if (id === editingId) return;
    const s = S();
    for (const x of [editingId, id]) { if (x && s && s.has(x)) { const r = D.get(x); if (r) addOld(r); pending.add(x); } }
    editingId = id || null;
    schedule();
  }
  function clearCaches() { clearCache(); D.clear(); pathCache.clear(); resEpoch++; sceneFull = true; schedule(); }

  const api = HD.render = {
    init, view, setView, zoomToFit, invalidate, screenToWorld, worldToScreen, hitTest, nodesInRect, addOverlay,
    drawNode, toCanvas, toSVG, image,
    /* helpers beyond the contract */
    resize, flush, on, stats, debug, hitChain, setEditing, loadFont, fontLoaded, ready, exportBounds, clearCaches,
    bounds: boundsOf, worldMatrix: worldMat, assetURL: null, webFonts: true, pixelGrid: true, frameLabels: true, zoomPreview: true, showGrids: true,
    /* path + boolean geometry, shared with hd-vector.js (vector edit, flatten): all pure */
    geom: {parsePath, segsToD, pathBBox, vectorSegs, outlineSegs, gridSpans, isBool(n) { return !!n && dtype(n) === 'BOOL'; },
      /* the outline of a boolean group as path data in the group's own space ('' when nothing is left) */
      boolPath(id) { const n = S().get(id); if (!n || dtype(n) !== 'BOOL') return null; const g = boolGeom(n, id, null, null); return {d: g.d, rule: g.rule, ok: g.ok}; },
      /* a boolean of layers that are not a group (yet): the outline of op(ids...) as path data in the space of `parent`
         (ids bottom first; text and lines take no part); null when nothing takes part */
      combine(op, ids, parent) {
        const s = S(), W0 = {curves: []}, ops = [], pm = inv(worldMat(parent));
        for (const id of ids) { const n = s.get(id); if (!n) continue; const o = operandOf(n, id, null, mul(pm, worldMat(n.parent)), 1, W0); if (o) ops.push(o); else if (op === 'subtract' && !ops.length) return null; }
        if (!ops.length) return null;
        const r = boolCompute(ops.length === 1 ? ops[0] : {op: BOOL[op] === 1 ? op : 'union', kids: ops}, W0.curves);
        return r ? r.d : null;
      }},
    get canvas() { return canvas; }, get dpr() { return dpr; }, get size() { return {w: cssW, h: cssH}; },
    get cacheCapMB() { return CACHE_CAP / 1048576; }, set cacheCapMB(v) { CACHE_CAP = Math.max(1, +v || 256) * 1048576; evict(); }
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', hook); else setTimeout(hook, 0);
})();

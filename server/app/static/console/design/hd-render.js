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
  const F_FX = 1, F_BG = 2, F_INST = 4, F_TEXT = 8, F_IMG = 16, F_MASKKID = 32, F_UP = F_BG | F_INST | F_IMG | F_TEXT;
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
  let editingId = null, pruneDue = false, lastFullMs = 0, lastRealAt = 0, forceReal = false, zoomTimer = 0;
  const pending = new Set();               /* node ids changed since the last paint */
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
  function gradient(ctx, p, w, h) {
    const c = gradCache.get(p);
    if (c !== undefined && c.w === w && c.h === h) return c.g;
    const stops = Array.isArray(p.stops) && p.stops.length ? p.stops : [{pos: 0, color: '#000000'}, {pos: 1, color: '#FFFFFF'}];
    let g = null;
    const lin = p.type === 'linear';
    const f = Array.isArray(p.from) ? p.from : (lin ? [0.5, 0] : [0.5, 0.5]);
    const t = Array.isArray(p.to) ? p.to : (lin ? [0.5, 1] : [1, 0.5]);
    const fx = num(+f[0], 0.5) * w, fy = num(+f[1], 0) * h, tx = num(+t[0], 0.5) * w, ty = num(+t[1], 1) * h;
    try {
      if (lin) g = ctx.createLinearGradient(fx, fy, tx, ty);
      else if (p.type === 'radial') g = ctx.createRadialGradient(fx, fy, 0, fx, fy, Math.max(0.01, Math.hypot(tx - fx, ty - fy)));
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
  /* path data -> absolute segments ['M',x,y] ['L',x,y] ['C',x1,y1,x2,y2,x,y] ['Z'] */
  function parsePath(d) {
    const out = [];
    const tok = String(d).match(/[a-zA-Z]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?/g) || [];
    let i = 0, cmd = '', cx = 0, cy = 0, sx = 0, sy = 0, lx = 0, ly = 0, lc = '', guard = 0;
    const nx = () => { const v = +tok[i++]; return v === v ? v : 0; };
    while (i < tok.length && guard++ < 200000) {
      if (/[a-zA-Z]/.test(tok[i])) cmd = tok[i++];
      else if (!cmd) { i++; continue; }
      const rel = cmd === cmd.toLowerCase(), C = cmd.toUpperCase();
      const ox = rel ? cx : 0, oy = rel ? cy : 0;
      if (C === 'Z') { out.push(['Z']); cx = sx; cy = sy; lc = C; cmd = ''; continue; }
      if (i >= tok.length) break;
      if (C === 'M') { cx = nx() + ox; cy = nx() + oy; sx = cx; sy = cy; out.push(['M', cx, cy]); cmd = rel ? 'l' : 'L'; }
      else if (C === 'L') { cx = nx() + ox; cy = nx() + oy; out.push(['L', cx, cy]); }
      else if (C === 'H') { cx = nx() + ox; out.push(['L', cx, cy]); }
      else if (C === 'V') { cy = nx() + oy; out.push(['L', cx, cy]); }
      else if (C === 'C') { const a = nx() + ox, b = nx() + oy, c = nx() + ox, e = nx() + oy, x = nx() + ox, y = nx() + oy; out.push(['C', a, b, c, e, x, y]); lx = c; ly = e; cx = x; cy = y; }
      else if (C === 'S') { const sm = lc === 'C' || lc === 'S', a = sm ? 2 * cx - lx : cx, b = sm ? 2 * cy - ly : cy, c = nx() + ox, e = nx() + oy, x = nx() + ox, y = nx() + oy; out.push(['C', a, b, c, e, x, y]); lx = c; ly = e; cx = x; cy = y; }
      else if (C === 'Q') { const qx = nx() + ox, qy = nx() + oy, x = nx() + ox, y = nx() + oy; out.push(['C', cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy), x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y), x, y]); lx = qx; ly = qy; cx = x; cy = y; }
      else if (C === 'T') { const sm = lc === 'Q' || lc === 'T', qx = sm ? 2 * cx - lx : cx, qy = sm ? 2 * cy - ly : cy, x = nx() + ox, y = nx() + oy; out.push(['C', cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy), x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y), x, y]); lx = qx; ly = qy; cx = x; cy = y; }
      else if (C === 'A') { const rx = nx(), ry = nx(), ph = nx(), fa = nx() ? 1 : 0, fs = nx() ? 1 : 0, x = nx() + ox, y = nx() + oy, cs = []; arcToCubics(cx, cy, rx, ry, ph, fa, fs, x, y, cs); for (const q of cs) out.push(['C', q[0], q[1], q[2], q[3], q[4], q[5]]); cx = x; cy = y; }
      else { i++; continue; }
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
  /* the scale that fits a VECTOR's path (written for its box) into the box it has now */
  function vecScale(d, w, h) {
    const b = pathBBox(d);
    let sx = 1, sy = 1;
    if (b.x1 > EPS && Math.abs(b.x1 - w) > Math.max(0.02, 0.002 * w)) sx = w / b.x1;
    if (b.y1 > EPS && Math.abs(b.y1 - h) > Math.max(0.02, 0.002 * h)) sy = h / b.y1;
    return [sx, sy, b.closed];
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
  function geomOf(n, type, w, h) {
    if (type === 'ELLIPSE') return G_ELL;
    if (type === 'LINE') return G_LINE;
    if (type === 'VECTOR') {
      const d = typeof n.path === 'string' ? n.path : '';
      const rule = n.fillRule === 'evenodd' ? 'evenodd' : 'nonzero';
      return cachePath('V' + rule + '|' + w + '|' + h + '|' + d, () => {
        let p;
        const sc = vecScale(d, w, h);
        try { p = new Path2D(d); } catch (e) { p = new Path2D(); }
        if (sc[0] !== 1 || sc[1] !== 1) { const q = new Path2D(); try { q.addPath(p, new DOMMatrix([sc[0], 0, 0, sc[1], 0, 0])); p = q; } catch (e) { /* unscaled */ } }
        return {k: R_PATH, r: null, p, rule, open: !sc[2], inv: null};
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
      wx0: 0, wy0: 0, wx1: 0, wy1: 0, serial: 0, tl: null, vt: null, vtk: ''};
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
      else if (type === 'VECTOR' || type === 'POLYGON' || type === 'STAR' || type === 'TEXT') so = sw * 2 + 1;
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
    const v = {n: rootN, id: inst.comp, key, kids: [], sx: 1, sy: 1, count: 1, flags: 0, ext: null};
    const cw = W(comp), ch = H(comp);
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
    const fx = fxList(n);
    if (fx) for (let i = 0; i < fx.length; i++) if (fx[i].type === 'bgblur') v.flags |= F_BG;
    return v;
  }
  function instTree(id, n, r) {
    const key = r.cv + ':' + compEpoch + ':' + resEpoch;
    if (r.vt !== null && r.vtk === key) return r.vt;
    r.vt = instRoot(n, [], 0, id, new Set());
    r.vtk = key;
    return r.vt;
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
  const CACHE_CAP = 256 * 1024 * 1024, CACHE_MAXD = 4096, CACHE_MAXA = 6e6, COST_MIN = 14, HOT_MS = 260;
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
    if (!T.canBuild || rec.hot > T.now || now() > T.budgetEnd) return false;
    let sc, bw, bh, offX, offY;
    if (axis) {
      const px0 = Math.floor(dx0), py0 = Math.floor(dy0);
      bw = Math.ceil(dx1) - px0; bh = Math.ceil(dy1) - py0;
      sc = ma; offX = me - px0; offY = mf - py0;
    } else {
      if (T.exact) return false;
      sc = Math.sqrt(Math.abs(ma * md - mb * mc));
      bw = Math.ceil((rec.x1 - rec.x0) * sc) + 2; bh = Math.ceil((rec.y1 - rec.y0) * sc) + 2;
      offX = -rec.x0 * sc + 1; offY = -rec.y0 * sc + 1;
    }
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
    if (axis) blitExact(T, en, op, blendOp, me, mf); else blitScaled(T, en, op, blendOp, ma, mb, mc, md, me, mf);
    if (cacheBytes > CACHE_CAP) evict();
    return true;
  }

  /* ------------------------------------------------------------------ painting */
  function paintKidsFrom(T, id, v, start, a, b, c, d, e, f) {
    if (v !== null) {
      const ks = v.kids;
      for (let i = start; i < ks.length; i++) {
        const k = ks[i];
        if (k.n.mask === true && k.n.visible !== false) { paintMasked(T, id, v, i, k.n, k.key, k, a, b, c, d, e, f); return; }
        paintNode(T, k.n, k.key, k, a, b, c, d, e, f);
      }
      return;
    }
    const s = S(), ks = s.children(id);
    for (let i = start; i < ks.length; i++) {
      const cn = s.get(ks[i]);
      if (cn === undefined) continue;
      if (cn.mask === true && cn.visible !== false) { paintMasked(T, id, null, i, cn, ks[i], null, a, b, c, d, e, f); return; }
      paintNode(T, cn, ks[i], null, a, b, c, d, e, f);
    }
  }
  /* a mask clips every later sibling to its own shape (its own picture is not drawn) */
  function paintMasked(T, pid, pv, i, mn, mid, mv, a, b, c, d, e, f) {
    const ctx = T.ctx, w = W(mn), h = H(mn);
    localMat(mn, LM);
    const ma = a * LM[0] + c * LM[1], mb = b * LM[0] + d * LM[1], mc = a * LM[2] + c * LM[3], md = b * LM[2] + d * LM[3], me = a * LM[4] + c * LM[5] + e, mf = b * LM[4] + d * LM[5] + f;
    if (GEO_MASK[mn.type] === 1) {
      ctx.save();
      ctx.setTransform(ma, mb, mc, md, me, mf);
      clipGeom(ctx, geomOf(mn, mn.type, w, h), w, h);
      paintKidsFrom(T, pid, pv, i + 1, a, b, c, d, e, f);
      ctx.restore();
      return;
    }
    let x0 = 0, y0 = 0, x1 = w, y1 = h;
    if (mv === null) { const r = derive(mid, mn); x0 = r.x0; y0 = r.y0; x1 = r.x1; y1 = r.y1; } else { const ex = vExt(mv); x0 = ex[0]; y0 = ex[1]; x1 = ex[2]; y1 = ex[3]; }
    boxUnder(ma, mb, mc, md, me, mf, x0, y0, x1, y1);
    const B = T.bounds;
    const lx0 = Math.max(Math.floor(BX[0]) - 1, B[0]), ly0 = Math.max(Math.floor(BX[1]) - 1, B[1]), lx1 = Math.min(Math.ceil(BX[2]) + 1, B[2]), ly1 = Math.min(Math.ceil(BX[3]) + 1, B[3]);
    const LW = lx1 - lx0, LH = ly1 - ly0;
    if (LW <= 0 || LH <= 0 || LW * LH > 5e7) return;
    const saveLD = LD;
    try {
      const A = getLayer(LW, LH), Bm = getLayer(LW, LH);
      stats.layers += 2;
      paintKidsFrom(subT(T, A.ctx, lx0, ly0, LW, LH), pid, pv, i + 1, a, b, c, d, e - lx0, f - ly0);
      const mask2 = mn.opacity === undefined && mn.blend === undefined ? mn : Object.assign({}, mn, {opacity: 1, blend: 'normal'});
      paintNode(subT(T, Bm.ctx, lx0, ly0, LW, LH), mask2, mid, mv, a, b, c, d, e - lx0, f - ly0);
      A.ctx.setTransform(1, 0, 0, 1, 0, 0);
      A.ctx.globalAlpha = 1; A.ctx.globalCompositeOperation = 'destination-in';
      A.ctx.drawImage(Bm.cv, 0, 0, LW, LH, 0, 0, LW, LH);
      A.ctx.globalCompositeOperation = 'source-over';
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalAlpha = 1;
      ctx.drawImage(A.cv, 0, 0, LW, LH, lx0, ly0, LW, LH);
    } finally { LD = saveLD; }
  }

  function paintNode(T, n, id, v, a, b, c, d, e, f) {
    if (n === undefined || n === null || n.visible === false) return;
    if (n.bind !== undefined && G(n, 'visible') === false) return;
    const type = n.type;
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
    if (op === undefined) op = 1; else { if (n.bind !== undefined) op = G(n, 'opacity'); op = num(+op, 1); if (op > 1) op = 1; }
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
    if (rec !== null && T.cache && rec.cost >= COST_MIN && (rec.flags & F_BG) === 0) {
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
    const g = type === 'TEXT' || type === 'GROUP' || type === 'LINE' ? null : geomOf(n, type, w, h);
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
    if (LW <= 0 || LH <= 0 || LW * LH > 5e7) return;
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
          const s = drops[i];
          fc.save();
          fc.shadowColor = rgba(s.color || '#000000', s.opacity === undefined ? 0.25 : s.opacity);
          fc.shadowBlur = Math.max(0, num(+s.blur, 0)) * scale;
          fc.shadowOffsetX = FAR + (ma * num(+s.x, 0) + mc * num(+s.y, 0)); fc.shadowOffsetY = mb * num(+s.x, 0) + md * num(+s.y, 0);
          fc.drawImage(Cn.cv, 0, 0, LW, LH, -FAR, 0, LW, LH);
          fc.restore();
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
      fillGeom(ctx, g, w, h, 0);
    }
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
      if (!vis(p) || !usePaint(ctx, p, w, h, alpha, true)) continue;
      strokeGeom(ctx, g, w, h, sw, align);
    }
    if (hasDash) ctx.setLineDash(NODASH);
  }

  /* fills, inner shadows, children, strokes of one node, drawn with matrix m (no group opacity here) */
  function paintContent(T, n, id, v, rec, type, w, h, alpha, inners, scale, ma, mb, mc, md, me, mf) {
    const ctx = T.ctx;
    if (type === 'TEXT') { ctx.setTransform(ma, mb, mc, md, me, mf); paintText(T, ctx, n, rec, w, h, alpha, scale); return; }
    if (type === 'GROUP' || type === 'PAGE') { paintKidsFrom(T, id, v, 0, ma, mb, mc, md, me, mf); return; }
    const g = geomOf(n, type, w, h);
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
    const hasStroke = strokes.length !== 0 && sw > 0 && anyVis(strokes), outside = hasStroke && G(n, 'strokeAlign') === 'outside';
    const doStroke = (width) => {
      ctx.lineJoin = G(n, 'strokeJoin') === 'miter' ? 'miter' : 'round'; ctx.miterLimit = 4; ctx.lineWidth = width;
      for (let i = 0; i < strokes.length; i++) { const p = strokes[i]; if (vis(p) && usePaint(ctx, p, w, h, alpha, true)) { textPass(ctx, lay, false, true); textPass(ctx, lay, true, true); } }
    };
    if (outside) doStroke(sw * 2);
    let ownRuns = false;
    for (let i = 0; i < lay.lines.length && !ownRuns; i++) { const sg = lay.lines[i].segs; for (let j = 0; j < sg.length; j++) if (sg[j].st.fills !== undefined) { ownRuns = true; break; } }
    for (let i = 0; i < fills.length; i++) { const p = fills[i]; if (vis(p) && usePaint(ctx, p, w, h, alpha, false)) textPass(ctx, lay, false, false); }
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
    if (hasStroke && !outside) doStroke(sw);
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
        if (r !== undefined) { addOld(r); bumpUp(r.par, stamp, t); D.delete(id); }
        const en = C.get(id);
        if (en !== undefined) dropEntry(id, en);
        pruneDue = true; any = true;
        continue;
      }
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
    D.clear(); clearCache(); pending.clear(); damage = [];
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
        lastZoomAt = t0;
        clearTimeout(zoomTimer);
        zoomTimer = setTimeout(() => { zoomTimer = 0; forceReal = true; schedule(); }, 90);
        present(pn, page, bs, tx, ty, {k, ox: tx - last.tx * k, oy: ty - last.ty * k});
        stats.ms = now() - t0; stats.mode = 'preview'; stats.frames++;
        emit('view', view);
        emit('frame', stats);
        return;
      }
    }
    forceReal = false;
    if (sceneFull || viewChanged || page !== last.page || pending.size > 0 || damage.length > 0) {
      let full = sceneFull || !last.valid || page !== last.page || bs !== last.s || debug.noDirty;
      const zooming = last.valid && bs !== last.s;
      if (zooming) lastZoomAt = t0;
      const exact = wantExact && !zooming;
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
      if (exact && full) wantExact = false;
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
  function hitShape(n, type, w, h, x, y, tol) {
    if (type === 'TEXT') return x >= -tol && x <= w + tol && y >= -tol && y <= h + tol;
    const sw = anyVis(L.paints(n, 'strokes')) ? Math.max(0, num(+G(n, 'strokeWeight'), 1)) : 0;
    if (type === 'LINE') return x >= -tol && x <= w + tol && Math.abs(y) <= Math.max(sw / 2, tol);
    const g = geomOf(n, type, w, h);
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
        if (j >= 0) { const mn = v !== null ? ks[j].n : s.get(ks[j]); toLocal(mn, x, y, P); if (!(P[0] >= 0 && P[1] >= 0 && P[0] <= W(mn) && P[1] <= H(mn))) continue; }
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
    const x = P[0], y = P[1], type = n.type, w = W(n), h = H(n);
    let rec = null;
    if (v === null) {
      rec = derive(id, n);
      if (x < rec.x0 - tol || x > rec.x1 + tol || y < rec.y0 - tol || y > rec.y1 + tol) return null;
    }
    const real = v === null;
    if (type === 'INSTANCE' && real) { v = instTree(id, n, rec); n = v.n; }
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
      if (type === 'VECTOR') {
        const d = typeof n.path === 'string' ? n.path : '', sc = vecScale(d, w, h);
        let out = '';
        for (const sg of parsePath(d)) {
          if (sg[0] === 'Z') out += 'Z';
          else if (sg[0] === 'C') out += 'C' + fnum(sg[1] * sc[0]) + ' ' + fnum(sg[2] * sc[1]) + ' ' + fnum(sg[3] * sc[0]) + ' ' + fnum(sg[4] * sc[1]) + ' ' + fnum(sg[5] * sc[0]) + ' ' + fnum(sg[6] * sc[1]);
          else out += sg[0] + fnum(sg[1] * sc[0]) + ' ' + fnum(sg[2] * sc[1]);
        }
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
      if (p.type === 'angular') { const c = hex6(stops[0].color); return [c[0], c[1] * po * (stops[0].opacity === undefined ? 1 : stops[0].opacity)]; }
      const lin = p.type === 'linear';
      const f = Array.isArray(p.from) ? p.from : (lin ? [0.5, 0] : [0.5, 0.5]), t = Array.isArray(p.to) ? p.to : (lin ? [0.5, 1] : [1, 0.5]);
      const fx = num(+f[0], 0.5) * w, fy = num(+f[1], 0) * h, tx = num(+t[0], 0.5) * w, ty = num(+t[1], 1) * h;
      const gid = nid('g');
      let st = '';
      for (const sp of stops) { if (!sp) continue; const c = hex6(sp.color), o = c[1] * (sp.opacity === undefined ? 1 : sp.opacity); st += '<stop offset="' + fnum(Math.max(0, Math.min(1, num(+sp.pos, 0)))) + '" stop-color="' + c[0] + '"' + (o < 1 ? ' stop-opacity="' + fnum(o) + '"' : '') + '/>'; }
      if (lin) defs.push('<linearGradient id="' + gid + '" gradientUnits="userSpaceOnUse" x1="' + fnum(fx) + '" y1="' + fnum(fy) + '" x2="' + fnum(tx) + '" y2="' + fnum(ty) + '">' + st + '</linearGradient>');
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
      const pathy = type === 'VECTOR' || type === 'POLYGON' || type === 'STAR';
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
      const strokes = L.paints(n, 'strokes'), sw = num(+G(n, 'strokeWeight'), 1);
      let strokeA = '';
      for (const p of strokes) if (vis(p) && sw > 0 && p.type !== 'image') { const r = paintRef(p, w, h), outside = G(n, 'strokeAlign') === 'outside'; strokeA = ' stroke="' + r[0] + '"' + (r[1] < 1 ? ' stroke-opacity="' + fnum(r[1]) + '"' : '') + ' stroke-width="' + fnum(outside ? sw * 2 : sw) + '" stroke-linejoin="round"' + (outside ? ' paint-order="stroke"' : ''); }
      let out = '<text xml:space="preserve" fill="' + fill[0] + '"' + (fill[1] < 1 ? ' fill-opacity="' + fnum(fill[1]) + '"' : '') + strokeA + '>';
      for (const ln of lay.lines) for (const sg of ln.segs) {
        if (sg.sp && sg.st.deco === 'none') continue;
        const st = sg.st;
        let a = ' x="' + fnum(sg.x) + '" y="' + fnum(ln.base) + '" font-family="' + esc(st.font) + ', Inter, sans-serif" font-size="' + fnum(st.size) + '" font-weight="' + st.weight + '"';
        if (st.italic) a += ' font-style="italic"';
        if (st.ls) a += ' letter-spacing="' + fnum(st.ls) + '"';
        if (st.deco === 'underline') a += ' text-decoration="underline"'; else if (st.deco === 'strike') a += ' text-decoration="line-through"';
        if (Array.isArray(st.fills)) for (const p of st.fills) if (vis(p) && p.type !== 'image') { const r = paintRef(p, w, h); a += ' fill="' + r[0] + '"' + (r[1] < 1 ? ' fill-opacity="' + fnum(r[1]) + '"' : ''); }
        out += '<tspan' + a + '>' + esc(sg.text) + '</tspan>';
      }
      return out + '</text>';
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
          body += (sp > 0 ? '<feMorphology in="SourceAlpha" operator="dilate" radius="' + fnum(sp) + '" result="' + r + 'm"/>' : '') +
            '<feGaussianBlur in="' + (sp > 0 ? r + 'm' : 'SourceAlpha') + '" stdDeviation="' + sd + '" result="' + r + 'b"/><feOffset in="' + r + 'b" dx="' + fnum(e.x) + '" dy="' + fnum(e.y) + '" result="' + r + 'o"/>' +
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
          const mid = nid('m');
          const mk = Object.assign({}, kn, {mask: false});
          defs.push('<mask id="' + mid + '" style="mask-type:alpha">' + node(mk, kid, kv) + '</mask>');
          return out + '<g mask="url(#' + mid + ')">' + kidsOf(id, v, list.slice(i + 1)) + '</g>';
        }
        out += node(kn, kid, kv);
      }
      return out;
    }
    function node(n, id, v) {
      if (!n || n.visible === false) return '';
      let type = n.type;
      const real = v === null;
      let rec = null;
      if (real) rec = derive(id, n);
      if (type === 'INSTANCE' && real) { v = instTree(id, n, rec); n = v.n; }
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
    bounds: boundsOf, worldMatrix: worldMat, assetURL: null, webFonts: true, pixelGrid: true, frameLabels: true, zoomPreview: true,
    get canvas() { return canvas; }, get dpr() { return dpr; }, get size() { return {w: cssW, h: cssH}; }
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', hook); else setTimeout(hook, 0);
})();

/* HOOLA DESIGN - layout engine (docs/HOOLA_DESIGN_PLAN.md section 3).
   HD.layout.run(changedIds)  text autoResize + auto layout + constraints + group bounds, written with HD.store.set
                              inside the caller's tx, only when a value really changes.
   HD.layout.measureText(node) -> {w, h, lines, lineHeight}   the ONE text layout the renderer draws from too.
   Plain browser JS, no dependencies, no eval. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const EPS = 0.01;
  const ST = () => HD.store;

  /* ------------------------------------------------------------------ defaults, styles, variables */
  const BASE = {
    x: 0, y: 0, w: 100, h: 100, rot: 0, flipH: false, flipV: false, visible: true, locked: false, opacity: 1, blend: 'normal',
    mask: false, strokeWeight: 1, strokeAlign: 'center', strokeCap: 'butt', strokeJoin: 'miter', radius: 0,
    sizeH: 'fixed', sizeV: 'fixed', layoutPos: 'auto', ratio: 0.5,
    font: 'Inter', fontSize: 16, fontWeight: 400, italic: false, lineHeight: 'auto', letterSpacing: 0, align: 'left',
    alignV: 'top', autoResize: 'wh', decoration: 'none', textCase: 'none'
  };
  const BY_TYPE = {
    FRAME: {clip: true}, COMPONENT: {clip: true}, INSTANCE: {clip: true}, POLYGON: {sides: 3}, STAR: {sides: 5},
    PAGE: {bg: '#F5F5F5'}, LINE: {h: 0}
  };
  let DEF = Object.create(null);
  function def(type) {
    let d = DEF[type];
    if (d) return d;
    d = Object.assign({}, BASE, BY_TYPE[type] || null);
    const s = ST();
    if (s && typeof s.defaults === 'function') { try { Object.assign(d, s.defaults(type) || null); } catch (e) { /* own table */ } }
    if (type === 'LINE') d.h = 0;
    DEF[type] = d;
    return d;
  }
  function rootNode() { const s = ST(); return (s && s.get(s.ROOT || '0:0')) || {}; }
  function varVal(vid) {
    const r = rootNode(), v = r.vars && r.vars[vid];
    if (!v || !v.modes) return undefined;
    const m = HD.layout.varMode || (Array.isArray(r.modes) ? r.modes[0] : undefined);
    if (m !== undefined && v.modes[m] !== undefined) return v.modes[m];
    for (const k in v.modes) return v.modes[k];
    return undefined;
  }
  function styleVal(sid, kind) {
    const r = rootNode(), s = r.styles && r.styles[sid];
    return s && (!kind || !s.kind || s.kind === kind) ? s.value : undefined;
  }
  /* G(node, prop): the value a node really has - a bound variable, else its own value, else the type default */
  function G(n, k) {
    const b = n.bind;
    if (b !== undefined && b !== null && b[k] !== undefined) { const v = varVal(b[k]); if (v !== undefined) return v; }
    const v = n[k];
    return v === undefined ? def(n.type)[k] : v;
  }
  function num(v, d) { return typeof v === 'number' && v === v && v !== Infinity && v !== -Infinity ? v : d; }
  function W(n) { return num(n.w, 100); }
  function H(n) { return n.type === 'LINE' ? 0 : num(n.h, 100); }
  function paints(n, key) {
    let a;
    if (key === 'fills' && n.fillStyle) { const sv = styleVal(n.fillStyle, 'fill'); if (sv !== undefined) a = Array.isArray(sv) ? sv : [sv]; }
    if (a === undefined) a = G(n, key);
    if (!Array.isArray(a) || !a.length) return NONE;
    const b = n.bind;
    if (b) {
      for (let i = 0; i < a.length; i++) {
        const vid = b[key + '.' + i + '.color'] || (i === 0 ? b[key === 'fills' ? 'fill' : 'stroke'] : undefined);
        if (vid === undefined) continue;
        const c = varVal(vid);
        if (typeof c === 'string') { a = a.slice(); a[i] = Object.assign({}, a[i], {color: c}); }
      }
    }
    return a;
  }
  const NONE = Object.freeze([]);
  function effects(n) {
    let a;
    if (n.effectStyle) { const sv = styleVal(n.effectStyle, 'effect'); if (sv !== undefined) a = Array.isArray(sv) ? sv : [sv]; }
    if (a === undefined) a = G(n, 'effects');
    return Array.isArray(a) && a.length ? a : NONE;
  }

  /* ------------------------------------------------------------------ text */
  const FALLBACK = 'Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans", "Noto Sans Devanagari", sans-serif';
  const TEXT_KEYS = ['font', 'fontSize', 'fontWeight', 'italic', 'lineHeight', 'letterSpacing', 'decoration', 'textCase'];
  const HAS_LS = typeof CanvasRenderingContext2D !== 'undefined' && 'letterSpacing' in CanvasRenderingContext2D.prototype;
  let mctx = null, fontEpoch = 1;
  const widths = new Map(), metrics = new Map(), layouts = new Map();
  function mc() {
    if (!mctx) { const c = document.createElement('canvas'); c.width = c.height = 4; mctx = c.getContext('2d'); }
    return mctx;
  }
  function famCss(f) { return '"' + String(f || 'Inter').replace(/["\\\n\r;{}<>]/g, '') + '", ' + FALLBACK; }
  function mkStyle(font, size, weight, italic, ls, lh, deco, tcase, fills) {
    size = Math.max(0.1, num(+size, 16)); weight = Math.round(num(+weight, 400)) || 400; ls = num(+ls, 0);
    const css = (italic ? 'italic ' : '') + weight + ' ' + size + 'px ' + famCss(font);
    return {font: String(font || 'Inter'), size, weight, italic: !!italic, ls, lh: typeof lh === 'number' && lh > 0 ? lh : 'auto',
      deco: deco || 'none', tcase: tcase || 'none', fills: fills, css, key: css + '|' + ls};
  }
  function baseStyle(n) {
    const ts = n.textStyle ? styleVal(n.textStyle, 'text') : undefined;
    const g = ts && typeof ts === 'object' ? (k) => (ts[k] !== undefined ? ts[k] : G(n, k)) : (k) => G(n, k);
    return mkStyle(g('font'), g('fontSize'), g('fontWeight'), g('italic'), g('letterSpacing'), g('lineHeight'), g('decoration'), g('textCase'), undefined);
  }
  function runStyle(b, r) {
    const p = (k, bk) => (r[k] !== undefined && r[k] !== null ? r[k] : b[bk]);
    let fills = r.fills;
    if (fills === undefined && typeof r.color === 'string') fills = [{type: 'solid', color: r.color}];
    return mkStyle(p('font', 'font'), p('fontSize', 'size'), p('fontWeight', 'weight'), p('italic', 'italic'), p('letterSpacing', 'ls'),
      p('lineHeight', 'lh'), p('decoration', 'deco'), p('textCase', 'tcase'), fills);
  }
  function setFont(c, st) {
    if (c.font !== st.css) c.font = st.css;
    if (HAS_LS) { const v = st.ls + 'px'; if (c.letterSpacing !== v) c.letterSpacing = v; }
  }
  function textWidth(text, st) {
    if (!text) return 0;
    const k = st.key + '\u0001' + text;
    let w = widths.get(k);
    if (w !== undefined) return w;
    const c = mc();
    setFont(c, st);
    w = c.measureText(text).width;
    if (!HAS_LS && st.ls) w += st.ls * Array.from(text).length;
    if (widths.size > 60000) widths.clear();
    widths.set(k, w);
    return w;
  }
  function fontMetrics(st) {
    let m = metrics.get(st.css);
    if (m) return m;
    const c = mc();
    setFont(c, st);
    const t = c.measureText('Hg');
    let a = t.fontBoundingBoxAscent, d = t.fontBoundingBoxDescent;
    if (!(a > 0)) { a = t.actualBoundingBoxAscent > 0 ? t.actualBoundingBoxAscent * 1.25 : st.size * 0.8; d = t.actualBoundingBoxDescent > 0 ? t.actualBoundingBoxDescent * 1.2 : st.size * 0.2; }
    m = {asc: a, desc: d || st.size * 0.2};
    metrics.set(st.css, m);
    return m;
  }
  function lineHeightOf(st) { return st.lh === 'auto' ? Math.round(st.size * 1.2 * 100) / 100 : st.lh; }
  function applyCase(t, tc, wordStart) {
    if (tc === 'upper') return t.toUpperCase();
    if (tc === 'lower') return t.toLowerCase();
    if (tc === 'title') return t.replace(/(^|[\s\-(\[{"'])(\S)/g, (m, a, b, i) => (i === 0 && !a && !wordStart ? m : a + b.toUpperCase()));
    return t;
  }
  const CJK = /[⺀-鿿豈-﫿＀-￯]/;
  function isSpace(ch) { return ch === ' ' || ch === '\t' || ch === '　'; }

  /* style segments of [0, len): [{s, e, st}] sorted, covering everything */
  function segments(n, len, base) {
    const runs = Array.isArray(n.runs) ? n.runs : null;
    if (!runs || !runs.length) return [{s: 0, e: len, st: base}];
    const cuts = new Set([0, len]);
    for (const r of runs) {
      if (!r) continue;
      const s = Math.max(0, Math.min(len, r.s | 0)), e = Math.max(0, Math.min(len, r.e | 0));
      if (e > s) { cuts.add(s); cuts.add(e); }
    }
    const pts = Array.from(cuts).sort((a, b) => a - b), out = [], memo = new Map();
    for (let i = 0; i + 1 < pts.length; i++) {
      const s = pts[i], e = pts[i + 1];
      let st = base, key = '';
      for (let j = 0; j < runs.length; j++) {
        const r = runs[j];
        if (r && (r.s | 0) <= s && (r.e | 0) >= e && (r.e | 0) > (r.s | 0)) { st = runStyle(st, r); key += j + ','; }
      }
      if (key) { const m = memo.get(key); if (m) st = m; else memo.set(key, st); }
      out.push({s, e, st});
    }
    return out.length ? out : [{s: 0, e: len, st: base}];
  }

  function layoutKey(n, chars, base, wrapW, boxH) {
    return chars + '\u0001' + base.key + '|' + base.lh + '|' + base.deco + '|' + base.tcase + '|' + (G(n, 'align') || 'left') + '|' +
      (G(n, 'alignV') || 'top') + '|' + wrapW + '|' + boxH + '|' + (n.runs ? JSON.stringify(n.runs) : '') + '|' + fontEpoch;
  }

  /* textLayout(node) -> {w, h, cw, ch, lines:[{x, y, w, h, base, text, segs:[{x, w, text, st}]}], lineHeight}
     w / h = the size the node should have under its autoResize; cw / ch = the size of the words themselves.
     Positions are relative to the node's own box. opts.sizeH / sizeV = 'fixed' forces that axis to the box. */
  function textLayout(n, opts) {
    const chars = String(G(n, 'chars') === undefined || G(n, 'chars') === null ? '' : G(n, 'chars'));
    const base = baseStyle(n);
    let mode = G(n, 'autoResize') || 'wh';
    if (opts && opts.mode) mode = opts.mode;
    const boxW = W(n), boxH = num(n.h, 100);
    const wrapW = mode === 'wh' ? Infinity : Math.max(0, boxW);
    const key = layoutKey(n, chars, base, wrapW + ':' + mode + ':' + (mode === 'wh' ? 0 : boxW), mode === 'none' ? boxH : -1);
    const hit = layouts.get(key);
    if (hit) return hit;
    const segs = segments(n, chars.length, base);
    const align = G(n, 'align') || 'left', alignV = G(n, 'alignV') || 'top';
    const lines = [];
    let si = 0, pos = 0;
    const paras = chars.split('\n');
    for (let pi = 0; pi < paras.length; pi++) {
      const para = paras[pi], ps = pos, pe = pos + para.length;
      pos = pe + 1;
      /* pieces: words and space runs, cut at style changes */
      const pieces = [];
      while (si < segs.length - 1 && segs[si].e <= ps) si++;
      let k = si, i = ps;
      while (i < pe) {
        while (k < segs.length - 1 && segs[k].e <= i) k++;
        const st = segs[k].st, lim = Math.min(pe, segs[k].e);
        const sp = isSpace(chars[i]);
        let j = i + 1;
        if (!sp && CJK.test(chars[i])) { /* one ideograph = one breakable piece */ }
        else while (j < lim && isSpace(chars[j]) === sp && !CJK.test(chars[j]) && !(chars[j - 1] === '-' && !sp)) j++;
        const raw = chars.slice(i, j);
        const text = st.tcase === 'none' ? raw : applyCase(raw, st.tcase, i === ps || isSpace(chars[i - 1]));
        const glue = !sp && i > ps && !isSpace(chars[i - 1]) && !CJK.test(chars[i - 1]) && !CJK.test(chars[i]) && chars[i - 1] !== '-';
        pieces.push({text, st, w: textWidth(text, st), sp, glue});
        i = j;
      }
      /* greedy lines */
      let cur = [], curW = 0, inkW = 0, first = true;
      const flush = (last) => { lines.push({pieces: cur, w: inkW, last, pi, empty: !cur.length, st: cur.length ? null : segStyleAt(segs, ps, base)}); cur = []; curW = 0; inkW = 0; first = false; };
      for (let a = 0; a < pieces.length;) {
        const p = pieces[a];
        if (p.sp) {
          if (cur.length || first) { cur.push(p); curW += p.w; }
          a++; continue;
        }
        let b = a + 1, ww = p.w;
        while (b < pieces.length && pieces[b].glue && !pieces[b].sp) { ww += pieces[b].w; b++; }
        if (inkW > 0 && curW + ww > wrapW + EPS) { trimTail(cur); flush(false); continue; }
        if (ww > wrapW + EPS && wrapW > 0 && wrapW !== Infinity) {
          /* a word wider than the box: break it by characters */
          for (let q = a; q < b; q++) {
            const pc = pieces[q], cps = Array.from(pc.text);
            let buf = '', bw = 0;
            for (const ch of cps) {
              const nw = textWidth(buf + ch, pc.st);
              if (buf && curW + nw > wrapW + EPS) {
                cur.push({text: buf, st: pc.st, w: bw, sp: false}); curW += bw; inkW = curW; flush(false);
                buf = ch; bw = textWidth(ch, pc.st);
              } else if (!buf && inkW > 0 && curW + nw > wrapW + EPS) { flush(false); buf = ch; bw = textWidth(ch, pc.st); }
              else { buf += ch; bw = nw; }
            }
            if (buf) { cur.push({text: buf, st: pc.st, w: bw, sp: false}); curW += bw; inkW = curW; }
          }
          a = b; continue;
        }
        for (let q = a; q < b; q++) cur.push(pieces[q]);
        curW += ww; inkW = curW;
        a = b;
      }
      trimTail(cur, true);
      flush(true);
    }
    /* merge same-style neighbours, measure, place */
    let cw = 0, ch = 0;
    const out = [];
    for (const L of lines) {
      const ps = L.pieces, merged = [];
      const justify = align === 'justify' && !L.last && wrapW !== Infinity;
      for (const p of ps) {
        const m = merged[merged.length - 1];
        if (m && m.st === p.st && !justify) { m.text += p.text; m.sp = m.sp && p.sp; }
        else merged.push({text: p.text, st: p.st, sp: p.sp, w: 0, x: 0});
      }
      let x = 0, lh = 0, asc = 0, desc = 0, ink = 0;
      for (const m of merged) {
        m.w = textWidth(m.text, m.st); m.x = x; x += m.w;
        if (!m.sp) ink = x;
        lh = Math.max(lh, lineHeightOf(m.st));
        const fm = fontMetrics(m.st);
        asc = Math.max(asc, fm.asc); desc = Math.max(desc, fm.desc);
      }
      if (!merged.length) { const st = L.st || base, fm = fontMetrics(st); lh = lineHeightOf(st); asc = fm.asc; desc = fm.desc; }
      /* spaces at the end of a wrapped line hang: they never push the line wider than its ink */
      const lw = L.last ? x : ink;
      out.push({x: 0, y: ch, w: lw, h: lh, base: ch + (lh - (asc + desc)) / 2 + asc, segs: merged, justify, text: merged.map(m => m.text).join('')});
      cw = Math.max(cw, lw); ch += lh;
    }
    const wAuto = Math.ceil(cw - 0.001), hAuto = Math.round(ch * 100) / 100;
    const w = mode === 'wh' ? wAuto : boxW, h = mode === 'none' ? boxH : hAuto;
    const dy = alignV === 'middle' ? (h - ch) / 2 : alignV === 'bottom' ? h - ch : 0;
    for (const L of out) {
      L.y += dy; L.base += dy;
      let lx = 0;
      if (L.justify) {
        const gaps = L.segs.filter((m, i) => m.sp && i > 0 && i < L.segs.length - 1);
        const extra = w - L.w;
        if (gaps.length && extra > 0) {
          const add = extra / gaps.length;
          let sh = 0;
          for (const m of L.segs) { m.x += sh; if (gaps.indexOf(m) >= 0) { m.w += add; sh += add; } }
          L.w = w;
        }
      } else if (align === 'center') lx = (w - L.w) / 2;
      else if (align === 'right') lx = w - L.w;
      L.x = lx;
      if (lx) for (const m of L.segs) m.x += lx;
    }
    const res = {w, h, cw: wAuto, ch: hAuto, lines: out, lineHeight: out.length ? out[0].h : lineHeightOf(base), mode};
    if (layouts.size > 6000) { let c = 0; for (const kk of layouts.keys()) { layouts.delete(kk); if (++c > 1500) break; } }
    layouts.set(key, res);
    return res;
  }
  function segStyleAt(segs, i, base) { for (const s of segs) if (i >= s.s && i < s.e) return s.st; return segs.length && i >= segs[segs.length - 1].e ? segs[segs.length - 1].st : base; }
  function trimTail(cur, keep) {
    /* wrapped lines drop the spaces that would start the next line; the last line of a paragraph keeps its own */
    if (keep) return;
  }

  function measureText(n) {
    if (!n) return {w: 0, h: 0, lines: [], lineHeight: 0};
    return textLayout(n);
  }
  function fontsChanged() { fontEpoch++; widths.clear(); metrics.clear(); layouts.clear(); }

  /* ------------------------------------------------------------------ run */
  const rec = new Map();          /* id -> {w, h, parent}: the size each container had when it was last laid out */
  let running = false, pendingSync = null;
  const CONTAINER = {FRAME: 1, COMPONENT: 1, COMPONENT_SET: 1, SECTION: 1, GROUP: 1, INSTANCE: 1};

  function remember(id) {
    const s = ST(), n = s.get(id);
    if (!n) { rec.delete(id); return; }
    let r = rec.get(id);
    if (!r) { r = {w: 0, h: 0, parent: undefined}; rec.set(id, r); }
    r.w = W(n); r.h = H(n); r.parent = n.parent;
  }
  function rememberAll() {
    rec.clear();
    const s = ST();
    if (!s || !s.get) return;
    const rootId = s.ROOT || '0:0', stack = [rootId];
    let guard = 0;
    while (stack.length && guard++ < 400000) {
      const id = stack.pop();
      remember(id);
      const kids = s.children(id) || [];
      for (let i = 0; i < kids.length; i++) stack.push(kids[i]);
    }
  }
  function depthOf(id) { const s = ST(); let d = 0, c = s.parent(id), g = 0; while (c && g++ < 2000) { d++; c = s.parent(c); } return d; }
  function hasLayout(n) { const l = n && n.layout; return !!(l && (l.mode === 'h' || l.mode === 'v') && n.type !== 'GROUP' && n.type !== 'INSTANCE'); }
  function inFlow(c) { return c && G(c, 'visible') !== false && G(c, 'layoutPos') !== 'absolute'; }
  function near(a, b) { return Math.abs(a - b) <= EPS; }
  function r2(v) { return Math.round(v * 100) / 100; }

  /* the one writer: only real changes reach the store */
  function put(id, vals) {
    const s = ST(), n = s.get(id);
    if (!n) return false;
    let out = null;
    for (const k in vals) {
      let v = vals[k];
      if (typeof v !== 'number' || v !== v) continue;
      v = r2(v);
      const cur = k === 'w' ? W(n) : k === 'h' ? H(n) : num(n[k], 0);
      if (Math.abs(cur - v) > EPS) { (out || (out = {}))[k] = v; }
    }
    if (!out) return false;
    s.set(id, out);
    return true;
  }

  /* which axes does a node size by itself (hug)? */
  function hugs(n, axisH) {
    if (n.type === 'TEXT') {
      const ar = G(n, 'autoResize') || 'wh', sz = G(n, axisH ? 'sizeH' : 'sizeV');
      if (sz === 'fill') return false;
      return axisH ? ar === 'wh' : ar !== 'none';
    }
    return hasLayout(n) && G(n, axisH ? 'sizeH' : 'sizeV') === 'hug';
  }
  function clampSize(c, v, axisH) {
    const mn = num(c[axisH ? 'minW' : 'minH'], 0), mx = num(c[axisH ? 'maxW' : 'maxH'], Infinity);
    if (mx >= mn && v > mx) v = mx;
    if (v < mn) v = mn;
    return v < 0 ? 0 : v;
  }

  /* TEXT: write the size its words need */
  function layoutText(id, ctx) {
    const s = ST(), n = s.get(id);
    if (!n) return;
    let mode = G(n, 'autoResize') || 'wh';
    if (mode === 'none') return;
    /* a text stretched by its auto layout parent keeps the given width and only grows down */
    if (mode === 'wh' && ctx && ctx.widthGiven && ctx.widthGiven.has(id)) mode = 'h';
    const t = textLayout(n, mode === (G(n, 'autoResize') || 'wh') ? null : {mode});
    put(id, mode === 'wh' ? {w: t.w, h: t.h} : {h: t.h});
  }

  /* CONSTRAINTS: a plain frame changed size -> move / stretch its children by their `cons` */
  function applyConstraints(id, ctx) {
    const s = ST(), n = s.get(id), r = rec.get(id);
    if (!n) return;
    const w1 = W(n), h1 = H(n);
    if (!r || (near(r.w, w1) && near(r.h, h1))) { remember(id); return; }
    const w0 = r.w, h0 = r.h;
    remember(id);
    const kids = s.children(id) || [];
    for (let i = 0; i < kids.length; i++) {
      const cid = kids[i], c = s.get(cid);
      if (!c || ctx.changed.has(cid)) continue;          /* a child set in this same tx is already where it should be */
      const cons = c.cons || {};
      let x = num(c.x, 0), y = num(c.y, 0), w = W(c), h = H(c);
      const dw = w1 - w0, dh = h1 - h0;
      switch (cons.h) {
        case 'right': x += dw; break;
        case 'leftright': w = Math.max(0, w + dw); break;
        case 'center': x += dw / 2; break;
        case 'scale': if (w0 > EPS) { x *= w1 / w0; w *= w1 / w0; } break;
        default: break;
      }
      if (c.type !== 'LINE') {
        switch (cons.v) {
          case 'bottom': y += dh; break;
          case 'topbottom': h = Math.max(0, h + dh); break;
          case 'center': y += dh / 2; break;
          case 'scale': if (h0 > EPS) { y *= h1 / h0; h *= h1 / h0; } break;
          default: break;
        }
      } else {
        switch (cons.v) { case 'bottom': y += dh; break; case 'center': y += dh / 2; break; case 'scale': if (h0 > EPS) y *= h1 / h0; break; default: break; }
      }
      const sized = !near(w, W(c)) || !near(h, H(c));
      if (c.type === 'GROUP' && sized) { scaleGroupKids(cid, W(c), H(c), w, h, ctx); put(cid, {x, y, w, h}); remember(cid); continue; }
      const vals = c.type === 'LINE' ? {x, y, w} : {x, y, w, h};
      if (c.type === 'TEXT' && sized && (G(c, 'autoResize') || 'wh') === 'wh') { delete vals.w; delete vals.h; }
      if (put(cid, vals) && sized) resized(cid, ctx, true);
    }
  }
  /* a group has no size of its own: scaling it scales what is inside */
  function scaleGroupKids(id, w0, h0, w1, h1, ctx) {
    const s = ST(), fx = w0 > EPS ? w1 / w0 : 1, fy = h0 > EPS ? h1 / h0 : 1;
    if (near(fx, 1) && near(fy, 1)) return;
    const kids = s.children(id) || [];
    for (let i = 0; i < kids.length; i++) {
      const cid = kids[i], c = s.get(cid);
      if (!c) continue;
      const w = W(c), h = H(c), nw = w * fx, nh = h * fy;
      if (c.type === 'GROUP') scaleGroupKids(cid, w, h, nw, nh, ctx);
      const vals = {x: num(c.x, 0) * fx, y: num(c.y, 0) * fy, w: nw};
      if (c.type !== 'LINE') vals.h = nh;
      if (c.type === 'TEXT' && (G(c, 'autoResize') || 'wh') === 'wh') { delete vals.w; delete vals.h; }
      if (put(cid, vals) && c.type !== 'GROUP') resized(cid, ctx, true);
      if (c.type === 'GROUP') remember(cid);
    }
  }

  /* the corners of a child's box in its parent's space */
  function localCorners(c) {
    const x = num(c.x, 0), y = num(c.y, 0), w = W(c), h = H(c), rot = num(c.rot, 0);
    if (!rot) return [x, y, x + w, y + h];
    const a = rot * Math.PI / 180, cs = Math.cos(a), sn = Math.sin(a), cx = x + w / 2, cy = y + h / 2;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (let i = 0; i < 4; i++) {
      const px = (i === 1 || i === 2 ? w : 0) - w / 2, py = (i >= 2 ? h : 0) - h / 2;
      const qx = cx + px * cs - py * sn, qy = cy + px * sn + py * cs;
      if (qx < x0) x0 = qx; if (qx > x1) x1 = qx; if (qy < y0) y0 = qy; if (qy > y1) y1 = qy;
    }
    return [x0, y0, x1, y1];
  }

  /* GROUP: its box hugs its children; the children keep their place on the page */
  function layoutGroup(id, ctx) {
    const s = ST(), n = s.get(id);
    if (!n) return;
    const kids = s.children(id) || [];
    if (!kids.length) { remember(id); return; }
    /* the group itself was resized by hand (and nothing inside was): scale what is inside to fit */
    const r = rec.get(id);
    if (r && ctx.changed.has(id) && (!near(r.w, W(n)) || !near(r.h, H(n)))) {
      let kidTouched = false;
      for (let i = 0; i < kids.length; i++) if (ctx.changed.has(kids[i])) { kidTouched = true; break; }
      if (!kidTouched) scaleGroupKids(id, r.w, r.h, W(n), H(n), ctx);
    }
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (let i = 0; i < kids.length; i++) {
      const c = s.get(kids[i]);
      if (!c) continue;
      const b = localCorners(c);
      if (b[0] < x0) x0 = b[0]; if (b[1] < y0) y0 = b[1]; if (b[2] > x1) x1 = b[2]; if (b[3] > y1) y1 = b[3];
    }
    if (x0 === Infinity) { remember(id); return; }
    const w1 = x1 - x0, h1 = y1 - y0;
    if (near(x0, 0) && near(y0, 0) && near(w1, W(n)) && near(h1, H(n))) { remember(id); return; }
    /* new box so that  M1 * (p - (x0, y0)) == M0 * p  for every point p inside */
    const w0 = W(n), h0 = H(n), gx = num(n.x, 0), gy = num(n.y, 0), rot = num(n.rot, 0);
    const a = rot * Math.PI / 180, cs = Math.cos(a), sn = Math.sin(a), fh = n.flipH ? -1 : 1, fv = n.flipV ? -1 : 1;
    const la = cs * fh, lb = sn * fh, lc = -sn * fv, ld = cs * fv;
    /* M0 * (x0, y0) */
    const px = x0 - w0 / 2, py = y0 - h0 / 2;
    const qx = gx + w0 / 2 + la * px + lc * py, qy = gy + h0 / 2 + lb * px + ld * py;
    const c1x = w1 / 2, c1y = h1 / 2;
    const nx = qx - c1x + (la * c1x + lc * c1y), ny = qy - c1y + (lb * c1x + ld * c1y);
    if (!near(x0, 0) || !near(y0, 0)) {
      for (let i = 0; i < kids.length; i++) { const c = s.get(kids[i]); if (c) put(kids[i], {x: num(c.x, 0) - x0, y: num(c.y, 0) - y0}); }
    }
    put(id, {x: nx, y: ny, w: w1, h: h1});
    remember(id);
  }

  /* AUTO LAYOUT: a thoughtful subset of flexbox. Measure, give out the free space, measure again, place. */
  function layoutAuto(id, ctx) {
    const s = ST(), n = s.get(id);
    if (!n) return;
    const L = n.layout, horiz = L.mode === 'h';
    const gap = num(L.gap, 0), pad = Array.isArray(L.pad) ? L.pad : [num(L.pad, 0), num(L.pad, 0), num(L.pad, 0), num(L.pad, 0)];
    const pt = num(pad[0], 0), pr = num(pad[1], 0), pb = num(pad[2], 0), pl = num(pad[3], 0);
    const padMain0 = horiz ? pl : pt, padMain1 = horiz ? pr : pb, padCross0 = horiz ? pt : pl, padCross1 = horiz ? pb : pr;
    const alignMain = L.alignMain || 'start', alignCross = L.alignCross || 'start';
    const hugMain = G(n, horiz ? 'sizeH' : 'sizeV') === 'hug', hugCross = G(n, horiz ? 'sizeV' : 'sizeH') === 'hug';
    const wrap = !!L.wrap && !hugMain;
    const gapCross = num(L.gapCross, gap);
    const kidsAll = s.children(id) || [], kids = [];
    for (let i = 0; i < kidsAll.length; i++) { const c = s.get(kidsAll[i]); if (inFlow(c)) kids.push(kidsAll[i]); }
    const mainOf = (c) => (horiz ? W(c) : H(c)), crossOf = (c) => (horiz ? H(c) : W(c));
    const setMain = (cid, v) => put(cid, horiz ? {w: v} : {h: v}), setCross = (cid, v) => put(cid, horiz ? {h: v} : {w: v});
    const fillsMain = (c) => !hugMain && c.type !== 'GROUP' && G(c, horiz ? 'sizeH' : 'sizeV') === 'fill' && !(c.type === 'LINE' && !horiz);
    const fillsCross = (c) => {
      if (c.type === 'GROUP' || (c.type === 'LINE' && horiz)) return false;
      const sz = G(c, horiz ? 'sizeV' : 'sizeH');
      if (sz === 'fill') return true;
      if (alignCross !== 'stretch' || sz === 'hug') return false;
      return !hugs(c, !horiz);
    };
    const innerMain = Math.max(0, mainOf(n) - padMain0 - padMain1);
    let innerCross = Math.max(0, crossOf(n) - padCross0 - padCross1);
    const given = (cid, axisH) => { if (axisH && ctx.widthGiven) ctx.widthGiven.add(cid); };

    /* 1. cross sizes that are already known (the container is not hugging that way, one line) */
    if (!hugCross && !wrap) {
      for (const cid of kids) {
        const c = s.get(cid);
        if (!fillsCross(c)) continue;
        if (!horiz) given(cid, true);
        if (setCross(cid, clampSize(c, innerCross, !horiz))) resized(cid, ctx, false);
        else if (!horiz && c.type === 'TEXT') resized(cid, ctx, false);
      }
    }
    /* 2. lines */
    const lines = [];
    if (wrap) {
      let cur = [], used = 0;
      for (const cid of kids) {
        const c = s.get(cid), m = fillsMain(c) ? clampSize(c, 0, horiz) : mainOf(c);
        if (cur.length && used + gap + m > innerMain + EPS) { lines.push(cur); cur = []; used = 0; }
        used += (cur.length ? gap : 0) + m; cur.push(cid);
      }
      if (cur.length) lines.push(cur);
    } else lines.push(kids.slice());
    /* 3. give the free main space to the fill children (min / max frozen first, like flex) */
    if (!hugMain) {
      for (const line of lines) {
        const flex = [];
        let fixed = 0;
        for (const cid of line) { const c = s.get(cid); if (fillsMain(c)) flex.push(cid); else fixed += mainOf(c); }
        if (!flex.length) continue;
        let free = innerMain - fixed - gap * (line.length - 1);
        const size = new Map();
        let open = flex.slice(), guard = 0;
        while (open.length && guard++ < 20) {
          const share = Math.max(0, free) / open.length;
          let frozen = false;
          for (const cid of open.slice()) {
            const c = s.get(cid), v = clampSize(c, share, horiz);
            if (!near(v, share)) { size.set(cid, v); free -= v; open.splice(open.indexOf(cid), 1); frozen = true; }
          }
          if (!frozen) { for (const cid of open) size.set(cid, share); open = []; }
        }
        for (const cid of flex) {
          if (horiz) given(cid, true);
          const c = s.get(cid);
          if (setMain(cid, size.get(cid) || 0)) resized(cid, ctx, false);
          else if (horiz && c.type === 'TEXT') resized(cid, ctx, false);
        }
      }
    }
    /* 4. cross size of each line, then stretch what fills it */
    const lineCross = [];
    for (const line of lines) {
      let mx = 0, any = false;
      for (const cid of line) { const c = s.get(cid); if (!fillsCross(c)) { mx = Math.max(mx, crossOf(c)); any = true; } }
      if (!any) for (const cid of line) { const c = s.get(cid); mx = Math.max(mx, clampSize(c, wrap || hugCross ? num(c[horiz ? 'minH' : 'minW'], crossOf(c)) : innerCross, !horiz)); }
      lineCross.push(wrap || hugCross ? mx : innerCross);
    }
    if (hugCross || wrap) {
      for (let li = 0; li < lines.length; li++) {
        for (const cid of lines[li]) {
          const c = s.get(cid);
          if (!fillsCross(c)) continue;
          if (!horiz) given(cid, true);
          if (setCross(cid, clampSize(c, lineCross[li], !horiz))) resized(cid, ctx, false);
        }
      }
      /* a stretched child may have grown the other way (text that wrapped): read the lines again */
      for (let li = 0; li < lines.length; li++) {
        let mx = 0, any = false;
        for (const cid of lines[li]) { const c = s.get(cid); if (!fillsCross(c)) { mx = Math.max(mx, crossOf(c)); any = true; } }
        if (any) lineCross[li] = mx;
      }
    }
    /* 5. the container's own hugging sizes */
    let usedCross = 0;
    for (let li = 0; li < lines.length; li++) usedCross += lineCross[li] + (li ? gapCross : 0);
    const own = {};
    if (hugMain) {
      let m = 0;
      for (const cid of kids) m += mainOf(s.get(cid));
      m += gap * Math.max(0, kids.length - 1) + padMain0 + padMain1;
      own[horiz ? 'w' : 'h'] = clampSize(n, m, horiz);
    }
    if (hugCross) own[horiz ? 'h' : 'w'] = clampSize(n, usedCross + padCross0 + padCross1, !horiz);
    put(id, own);
    const n2 = s.get(id), mainSize = mainOf(n2), crossSize = crossOf(n2);
    const availMain = Math.max(0, mainSize - padMain0 - padMain1);
    if (!wrap) lineCross[0] = Math.max(0, crossSize - padCross0 - padCross1);
    /* 6. place */
    let crossAt = padCross0;
    for (let li = 0; li < lines.length; li++) {
      const line = lines[li];
      let used = 0;
      for (const cid of line) used += mainOf(s.get(cid));
      let g = gap, at = padMain0;
      const free = availMain - used - gap * Math.max(0, line.length - 1);
      if (alignMain === 'center') at += free / 2;
      else if (alignMain === 'end') at += free;
      else if (alignMain === 'between' && line.length > 1) g = (availMain - used) / (line.length - 1);
      for (const cid of line) {
        const c = s.get(cid), cm = mainOf(c), cc = crossOf(c);
        let cr = crossAt;
        if (alignCross === 'center') cr += (lineCross[li] - cc) / 2;
        else if (alignCross === 'end') cr += lineCross[li] - cc;
        put(cid, horiz ? {x: at, y: cr} : {x: cr, y: at});
        at += cm + g;
      }
      crossAt += lineCross[li] + gapCross;
    }
    remember(id);
  }

  /* a node got a new size from above: let its inside follow */
  function resized(id, ctx, fromConstraints) {
    const s = ST(), n = s.get(id);
    if (!n) return;
    if (ctx.depth > 200) return;
    ctx.depth++;
    try {
      if (n.type === 'TEXT') layoutText(id, ctx);
      else if (n.type === 'GROUP' || n.type === 'INSTANCE') remember(id);
      else if (hasLayout(n)) layoutAuto(id, ctx);
      else if (CONTAINER[n.type]) applyConstraints(id, ctx);
    } finally { ctx.depth--; }
  }

  function layoutSelf(id, ctx) {
    const s = ST(), n = s.get(id);
    if (!n) return;
    if (n.type === 'TEXT') layoutText(id, ctx);
    else if (n.type === 'GROUP') layoutGroup(id, ctx);
    else if (n.type === 'INSTANCE') remember(id);
    else if (hasLayout(n)) layoutAuto(id, ctx);
    else if (CONTAINER[n.type]) applyConstraints(id, ctx);
  }

  function run(changedIds) {
    const s = ST();
    if (!s || !changedIds) return;
    const changed = changedIds instanceof Set ? changedIds : new Set(changedIds);
    if (!changed.size) return;
    if (running) return;                 /* our own writes never start a second walk */
    running = true;
    try {
      const ctx = {changed, depth: 0, widthGiven: new Set()};
      const buckets = [], queued = new Set();
      const add = (id) => {
        if (!id || queued.has(id) || !s.has(id)) return;
        const n = s.get(id);
        if (!n || n.type === 'DOCUMENT' || n.type === 'PAGE') return;
        queued.add(id);
        const d = depthOf(id);
        (buckets[d] || (buckets[d] = [])).push(id);
      };
      for (const id of changed) {
        const r = rec.get(id);
        if (s.has(id)) {
          add(id);
          const p = s.parent(id);
          add(p);
          if (r && r.parent && r.parent !== p) add(r.parent);      /* the frame it was moved out of */
        } else if (r) { add(r.parent); rec.delete(id); }             /* deleted: its old parent closes the gap */
      }
      /* deepest first; every node once; a node whose box changed wakes its parent */
      for (let d = buckets.length - 1; d >= 0; d--) {
        const b = buckets[d];
        if (!b) continue;
        for (let i = 0; i < b.length; i++) {
          const id = b[i], n0 = s.get(id);
          if (!n0) continue;
          const x0 = num(n0.x, 0), y0 = num(n0.y, 0), w0 = W(n0), h0 = H(n0);
          layoutSelf(id, ctx);
          const n1 = s.get(id);
          if (!n1) continue;
          if (changed.has(id) || !near(x0, num(n1.x, 0)) || !near(y0, num(n1.y, 0)) || !near(w0, W(n1)) || !near(h0, H(n1))) {
            const p = s.parent(id);
            if (p && !queued.has(p)) {
              const pd = depthOf(p);
              if (pd < d) add(p);
            }
          }
          const rr = rec.get(id);
          if (rr) rr.parent = n1.parent; else remember(id);
        }
      }
      for (const id of changed) if (s.has(id)) { const r = rec.get(id), n = s.get(id); if (r) { r.parent = n.parent; if (!CONTAINER[n.type]) { r.w = W(n); r.h = H(n); } } else remember(id); }
      if (pendingSync) for (const id of changed) pendingSync.delete(id);
    } finally { running = false; }
  }

  /* keep the size records true for changes that never pass through run(): remote ops, a fresh document */
  function onChange(ev) {
    if (!ev || !ev.ids) return;
    if (ev.remote) { for (const id of ev.ids) remember(id); return; }
    if (running) return;
    if (!pendingSync) {
      pendingSync = new Set();
      Promise.resolve().then(() => { const p = pendingSync; pendingSync = null; if (p) for (const id of p) if (!rec.has(id)) remember(id); });
    }
    for (const id of ev.ids) pendingSync.add(id);
  }
  let hooked = null;
  function hook() {
    const s = ST();
    if (!s || hooked === s || typeof s.on !== 'function') return;
    hooked = s;
    s.on('load', () => { DEF = Object.create(null); rememberAll(); });
    s.on('change', onChange);
    try { rememberAll(); } catch (e) { /* nothing loaded yet */ }
  }

  HD.layout = {
    run(changedIds) { hook(); return run(changedIds); },
    measureText,
    /* helpers beyond the contract (the renderer is built on them) */
    textLayout, fontsChanged, prop: G, paints, effects, defaultsOf: def, varValue: varVal, styleValue: styleVal,
    fontCss(n) { return baseStyle(n).css; }, baseStyle, setFont, hasLetterSpacing: HAS_LS, hasLayout,
    remember, rememberAll, hook, varMode: null,
    get fontEpoch() { return fontEpoch; }
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', hook); else setTimeout(hook, 0);
})();

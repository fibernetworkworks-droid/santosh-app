/* HOOLA DESIGN - D4 hand-off (docs/HOOLA_DESIGN_PLAN.md, phase D4): everything that leaves or enters a file.
   EXPORT   the Export section of the Design panel (per-node `exports` rows: format, size, suffix), the Export dialog
            (selection or every frame of the page, with the list of what will be made), Copy as PNG / SVG.
            PNG / JPG through HD.render.toCanvas, SVG through HD.render.toSVG, PDF with the writer below (one page per
            frame at its size in points; every page is ONE JPEG picture at 2x - the text in it can not be selected),
            several files in one store-only ZIP written here (CRC32, UTF-8 names). No dependency, no worker, no eval.
   IMPORT   SVG (file picker, drop, paste) parsed with DOMParser into an INERT document and rebuilt as real editable
            nodes; nothing in the SVG is ever run, put into the page or fetched (script, foreignObject, on* attributes,
            outside links and outside pictures are simply never read). Pictures (PNG / JPEG / WebP / GIF) become a
            rectangle with an image fill. Each import is ONE undo step.
   INSPECT  the Inspect tab of the right panel (also in view-only files): size, type, colours with click-to-copy,
            spacing, and code for the layer as CSS, Flutter and Tailwind.
   FILE     Save a copy as .hoola.json / Import a .hoola.json into a new file (the backup and move format).
   Public for tests and other phases: HD.handoff. Every document edit goes through HD.store inside one transaction;
   every text from a document or a file is set with textContent, never as HTML. */
(function () {
  'use strict';
  const HD = window.HD = window.HD || {};
  const M = HD.math;
  const S = () => HD.store, R = () => HD.render, LY = () => HD.layout, UI = () => HD.ui, U = () => HD.tools.u;
  const DEG = Math.PI / 180;
  const CONT = {FRAME: 1, COMPONENT: 1, COMPONENT_SET: 1, INSTANCE: 1, SECTION: 1};
  const TYPE_LABEL = {FRAME: 'Frame', GROUP: 'Group', SECTION: 'Section', RECT: 'Rectangle', ELLIPSE: 'Ellipse', LINE: 'Line', POLYGON: 'Polygon', STAR: 'Star',
    VECTOR: 'Vector', TEXT: 'Text', COMPONENT: 'Component', COMPONENT_SET: 'Component set', INSTANCE: 'Instance', PAGE: 'Page'};

  /* ================================================================ small helpers */
  function num(v, d) { return typeof v === 'number' && isFinite(v) ? v : d; }
  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function rnd(v, places) { const k = Math.pow(10, places === undefined ? 2 : places), r = Math.round(v * k) / k; return r === 0 ? 0 : r; }
  function fx(v, places) { return String(rnd(+v || 0, places)); }
  function commas(n) { return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
  function h() { return UI().h.apply(null, arguments); }
  function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
  function toast(msg, bad) { if (UI() && UI().toast) UI().toast(msg, bad); }
  function canEdit() { try { return !!U().canEdit(); } catch (e) { return false; } }
  function node(id) { return S().get(id); }
  function typeOf(id) { const n = node(id); return n ? n.type : ''; }
  function G(n, k) { return LY().prop(n, k); }                       /* the value a node really has (variable, own value, default) */
  function P(id, k) { const n = node(id); return n ? G(n, k) : undefined; }
  function Wn(n) { return num(n.w, 100); }
  function Hn(n) { return n.type === 'LINE' ? 0 : num(n.h, 100); }
  function vis(p) { return p !== null && typeof p === 'object' && p.visible !== false && (p.opacity === undefined || p.opacity > 0); }
  function fileName() { const f = HD.app && HD.app.file; return (f && f.name) || 'Hoola design'; }
  function lsGet(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private window */ } }
  function utf8(s) { return new TextEncoder().encode(String(s)); }
  function latin1(s) { const b = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) b[i] = s.charCodeAt(i) & 255; return b; }
  function blobBytes(blob) { return blob.arrayBuffer().then(b => new Uint8Array(b)); }
  function blobText(blob) { return blob.text(); }
  function tick() { return new Promise(res => setTimeout(res, 0)); }

  /* a layer name made safe as a file name: no path tricks, no characters a disk refuses, never empty */
  const RESERVED = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i;
  function safePart(s) {
    s = String(s === null || s === undefined ? '' : s).replace(/[\u0000-\u001F\u007F<>:"\\|?*\/]+/g, '-').replace(/\s+/g, ' ').trim();
    s = s.replace(/^[.\s-]+/, '').replace(/[.\s]+$/, '');
    if (s.length > 80) s = s.slice(0, 80).trim();
    if (RESERVED.test(s)) s = '_' + s;
    return s;
  }
  /* "icons/home" -> a folder inside a ZIP (folders = true) or "icons-home" (one file) */
  function safeName(name, folders) {
    const parts = String(name === null || name === undefined ? '' : name).split('/').map(safePart).filter(p => p && p !== '.' && p !== '..');
    if (!parts.length) return 'layer';
    return folders ? parts.slice(0, 6).join('/') : safePart(parts.join('-')) || 'layer';
  }
  function safeSuffix(s) { return String(s === null || s === undefined ? '' : s).replace(/[\u0000-\u001F\u007F<>:"\\|?*\/]+/g, '-').slice(0, 24); }

  /* ================================================================ CRC32 + ZIP (store only) + PDF */
  const CRC_T = (function () { const t = new Uint32Array(256); for (let i = 0; i < 256; i++) { let c = i; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[i] = c >>> 0; } return t; })();
  function crc32(bytes) { let c = 0xFFFFFFFF; for (let i = 0; i < bytes.length; i++) c = CRC_T[(c ^ bytes[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }

  /* files: [{name, data: Uint8Array}] -> Blob. Stored (no compression: PNG / JPG / PDF are packed already), names in
     UTF-8 (flag bit 11), no ZIP64: more than 65,535 files or 4 GB is refused. */
  function zip(files, when) {
    if (files.length > 65535) throw new Error('Too many files for one ZIP (65,535 is the most).');
    const d = when || new Date();
    const dosTime = ((d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1)) & 0xFFFF;
    const dosDate = (((Math.max(1980, d.getFullYear()) - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate()) & 0xFFFF;
    const parts = [], central = [];
    let offset = 0, cdSize = 0;
    for (const f of files) {
      const name = utf8(f.name), data = f.data, crc = crc32(data);
      if (name.length > 65535) throw new Error('A file name is too long for a ZIP.');
      const lh = new DataView(new ArrayBuffer(30));
      lh.setUint32(0, 0x04034B50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true); lh.setUint16(8, 0, true);
      lh.setUint16(10, dosTime, true); lh.setUint16(12, dosDate, true); lh.setUint32(14, crc, true); lh.setUint32(18, data.length, true); lh.setUint32(22, data.length, true);
      lh.setUint16(26, name.length, true); lh.setUint16(28, 0, true);
      const ch = new DataView(new ArrayBuffer(46));
      ch.setUint32(0, 0x02014B50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint16(8, 0x0800, true); ch.setUint16(10, 0, true);
      ch.setUint16(12, dosTime, true); ch.setUint16(14, dosDate, true); ch.setUint32(16, crc, true); ch.setUint32(20, data.length, true); ch.setUint32(24, data.length, true);
      ch.setUint16(28, name.length, true); ch.setUint16(30, 0, true); ch.setUint16(32, 0, true); ch.setUint16(34, 0, true); ch.setUint16(36, 0, true); ch.setUint32(38, 0, true); ch.setUint32(42, offset, true);
      parts.push(new Uint8Array(lh.buffer), name, data);
      central.push(new Uint8Array(ch.buffer), name);
      offset += 30 + name.length + data.length; cdSize += 46 + name.length;
      if (offset + cdSize > 0xFFFFFFF0) throw new Error('This export is over 4 GB, too big for one ZIP. Export fewer layers at a time.');
    }
    const end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054B50, true); end.setUint16(4, 0, true); end.setUint16(6, 0, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
    end.setUint32(12, cdSize, true); end.setUint32(16, offset, true); end.setUint16(20, 0, true);
    return new Blob(parts.concat(central, [new Uint8Array(end.buffer)]), {type: 'application/zip'});
  }

  /* width, height and colour channels of a JPEG, read from its own frame header */
  function jpegInfo(b) {
    if (b.length < 4 || b[0] !== 0xFF || b[1] !== 0xD8) return null;
    let i = 2;
    while (i + 9 < b.length) {
      if (b[i] !== 0xFF) { i++; continue; }
      const m = b[i + 1];
      if (m === 0xFF) { i++; continue; }
      if (m === 0xD8 || m === 0x01 || (m >= 0xD0 && m <= 0xD7)) { i += 2; continue; }
      const len = (b[i + 2] << 8) | b[i + 3];
      if (m >= 0xC0 && m <= 0xCF && m !== 0xC4 && m !== 0xC8 && m !== 0xCC) return {h: (b[i + 5] << 8) | b[i + 6], w: (b[i + 7] << 8) | b[i + 8], comps: b[i + 9], bits: b[i + 4]};
      if (len < 2) return null;
      i += 2 + len;
    }
    return null;
  }
  function pdfText(s) { let out = 'FEFF'; s = String(s); for (let i = 0; i < s.length; i++) out += ('000' + s.charCodeAt(i).toString(16).toUpperCase()).slice(-4); return '<' + out + '>'; }
  function pdfNum(v) { return String(Math.round(v * 100) / 100); }
  /* pages: [{w, h (points), jpeg: Uint8Array}] -> Blob: a small valid PDF, every page one JPEG (DCTDecode) drawn over
     the whole page. A page over 14,400 points (the limit of PDF readers) gets a UserUnit so its size stays true. */
  function pdf(pages, meta) {
    if (!pages.length) throw new Error('There is nothing to put in the PDF.');
    const chunks = [], offs = [];
    let pos = 0;
    const put = x => { const b = typeof x === 'string' ? latin1(x) : x; chunks.push(b); pos += b.length; };
    const open = n => { offs[n] = pos; put(n + ' 0 obj\n'); }, close = () => put('\nendobj\n');
    const big = pages.some(p => Math.max(p.w, p.h) > 14400);
    put(big ? '%PDF-1.6\n' : '%PDF-1.4\n'); put(new Uint8Array([0x25, 0xE2, 0xE3, 0xCF, 0xD3, 0x0A]));
    const N = pages.length, total = 3 + N * 3, pageNo = i => 4 + i * 3;
    open(1); put('<< /Type /Catalog /Pages 2 0 R >>'); close();
    open(2); put('<< /Type /Pages /Count ' + N + ' /Kids [' + pages.map((p, i) => pageNo(i) + ' 0 R').join(' ') + '] >>'); close();
    const d = (meta && meta.date) || new Date(), z = v => ('0' + v).slice(-2);
    const stamp = 'D:' + d.getUTCFullYear() + z(d.getUTCMonth() + 1) + z(d.getUTCDate()) + z(d.getUTCHours()) + z(d.getUTCMinutes()) + z(d.getUTCSeconds()) + 'Z';
    open(3); put('<< /Title ' + pdfText((meta && meta.title) || 'Hoola Design') + ' /Producer (Hoola Design) /Creator (Hoola Design) /CreationDate (' + stamp + ') >>'); close();
    pages.forEach((p, i) => {
      const info = jpegInfo(p.jpeg);
      if (!info || !(info.comps === 1 || info.comps === 3)) throw new Error('A page picture could not be read as a JPEG.');
      const longest = Math.max(p.w, p.h), uu = longest > 14400 ? Math.ceil(longest / 14400) : 1, pw = Math.max(1, p.w) / uu, ph = Math.max(1, p.h) / uu;
      const body = latin1('q\n' + pdfNum(pw) + ' 0 0 ' + pdfNum(ph) + ' 0 0 cm\n/Im0 Do\nQ\n');
      open(pageNo(i)); put('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ' + pdfNum(pw) + ' ' + pdfNum(ph) + ']' + (uu > 1 ? ' /UserUnit ' + uu : '') +
        ' /Resources << /ProcSet [/PDF /ImageC] /XObject << /Im0 ' + (pageNo(i) + 2) + ' 0 R >> >> /Contents ' + (pageNo(i) + 1) + ' 0 R >>'); close();
      open(pageNo(i) + 1); put('<< /Length ' + body.length + ' >>\nstream\n'); put(body); put('endstream'); close();
      open(pageNo(i) + 2); put('<< /Type /XObject /Subtype /Image /Width ' + info.w + ' /Height ' + info.h + ' /ColorSpace ' + (info.comps === 1 ? '/DeviceGray' : '/DeviceRGB') +
        ' /BitsPerComponent 8 /Filter /DCTDecode /Length ' + p.jpeg.length + ' >>\nstream\n'); put(p.jpeg); put('\nendstream'); close();
    });
    const xref = pos;
    let table = 'xref\n0 ' + (total + 1) + '\n0000000000 65535 f \n';
    for (let n = 1; n <= total; n++) table += ('0000000000' + offs[n]).slice(-10) + ' 00000 n \n';
    put(table + 'trailer\n<< /Size ' + (total + 1) + ' /Root 1 0 R /Info 3 0 R >>\nstartxref\n' + xref + '\n%%EOF\n');
    return new Blob(chunks, {type: 'application/pdf'});
  }

  /* ================================================================ the export engine */
  const FORMATS = [['png', 'PNG'], ['jpg', 'JPG'], ['svg', 'SVG'], ['pdf', 'PDF']];
  const FMT_OK = {png: 1, jpg: 1, svg: 1, pdf: 1};
  const MIME = {png: 'image/png', jpg: 'image/jpeg', svg: 'image/svg+xml', pdf: 'application/pdf'};
  const LIMIT_SIDE = 16384, LIMIT_AREA = 1.2e8;          /* what HD.render.toCanvas draws at full size; it shrinks beyond, we refuse */
  const SCALE_MIN = 0.1, SCALE_MAX = 8;

  function cleanRow(r) {
    r = r && typeof r === 'object' ? r : {};
    const out = {fmt: FMT_OK[r.fmt] ? r.fmt : 'png', scale: clamp(num(+r.scale, 1), SCALE_MIN, SCALE_MAX), suffix: typeof r.suffix === 'string' ? r.suffix : ''};
    if (num(+r.w, 0) >= 1) out.w = Math.round(clamp(+r.w, 1, LIMIT_SIDE)); else if (num(+r.h, 0) >= 1) out.h = Math.round(clamp(+r.h, 1, LIMIT_SIDE));
    return out;
  }
  function rowsOf(id) { const a = P(id, 'exports'); return Array.isArray(a) ? a.map(cleanRow) : []; }
  function sizeLabel(row) { return row.w ? row.w + 'w' : row.h ? row.h + 'h' : fx(row.scale, 2) + 'x'; }
  /* "2x" "0.5" "512w" "300h" -> the size part of a row, or null */
  function parseSize(text) {
    const s = String(text || '').trim().toLowerCase().replace(/,/g, '.').replace(/\s+/g, '');
    let m = /^(\d*\.?\d+)x?$/.exec(s);
    if (m) { const v = parseFloat(m[1]); if (!(v > 0)) return null; return {scale: rnd(clamp(v, SCALE_MIN, SCALE_MAX), 3)}; }
    m = /^(\d+)(?:px)?w$/.exec(s) || /^w(\d+)$/.exec(s);
    if (m) return +m[1] >= 1 ? {scale: 1, w: Math.round(clamp(+m[1], 1, LIMIT_SIDE))} : null;
    m = /^(\d+)(?:px)?h$/.exec(s) || /^h(\d+)$/.exec(s);
    if (m) return +m[1] >= 1 ? {scale: 1, h: Math.round(clamp(+m[1], 1, LIMIT_SIDE))} : null;
    return null;
  }
  /* a frame is exported as its own box (a 1080 x 1080 frame at 1x is 1080 x 1080 px); a shape with what it paints
     outside its box (stroke, shadow). outer = true keeps a frame's outside shadow too. */
  function boundsMode(id, outer) { return CONT[typeOf(id)] && !outer ? 'box' : 'paint'; }
  function boxOf(id, mode) { const b = R().exportBounds(id, mode); return b && b.w > 0 && b.h > 0 ? b : {x: 0, y: 0, w: Math.max(1, (b && b.w) || 1), h: Math.max(1, (b && b.h) || 1)}; }
  function px(v) { return Math.max(1, Math.ceil(v - 0.001)); }
  function fits(w, hh) { return w <= LIMIT_SIDE && hh <= LIMIT_SIDE && w * hh <= LIMIT_AREA; }
  function maxScaleFor(b) { const k = Math.min(LIMIT_SIDE / b.w, LIMIT_SIDE / b.h, Math.sqrt(LIMIT_AREA / (b.w * b.h))); return Math.floor(k * 100) / 100; }
  /* {scale, w, h (pixels), bw, bh (the box in design units), ok, max} for one row on one node */
  function sizeFor(id, row, outer) {
    const b = boxOf(id, boundsMode(id, outer));
    const scale = row.w ? row.w / b.w : row.h ? row.h / b.h : row.scale;
    const w = px(b.w * scale), hh = px(b.h * scale);
    return {scale: scale, w: w, h: hh, bw: b.w, bh: b.h, ok: fits(w, hh), max: maxScaleFor(b)};
  }
  function TooBig(name, sz) {
    const e = new Error('\u201C' + name + '\u201D would be ' + commas(sz.w) + ' \u00D7 ' + commas(sz.h) + ' px, more than a browser can draw. The largest size that works is ' +
      fx(sz.max, 2) + 'x (' + commas(px(sz.bw * sz.max)) + ' \u00D7 ' + commas(px(sz.bh * sz.max)) + ' px).');
    e.tooBig = true; e.max = sz.max; return e;
  }
  function canvasBlob(cv, mime, q) { return new Promise((res, rej) => { try { cv.toBlob(b => { if (b) res(b); else rej(new Error('The browser could not make this picture. Try a smaller size.')); }, mime, q); } catch (e) { rej(e); } }); }
  function pageBg(id) { const n = node(id); return n && n.type === 'PAGE' ? undefined : '#FFFFFF'; }

  /* one node + one row -> {blob, w, h}. Waits for the fonts and pictures of the subtree first. */
  async function renderOne(id, row, opts) {
    const n = node(id);
    if (!n) throw new Error('That layer is no longer in the file.');
    row = cleanRow(row); opts = opts || {};
    const name = n.name || TYPE_LABEL[n.type] || 'Layer', mode = boundsMode(id, opts.outer);
    await R().ready(id, 8000);
    if (row.fmt === 'pdf') { const p = await pdfPage(id, opts.outer); return {blob: pdf([p], {title: name}), w: Math.round(p.w), h: Math.round(p.h)}; }
    const sz = sizeFor(id, row, opts.outer);
    if (row.fmt === 'svg') {
      let svg = R().toSVG(id, {bounds: mode});
      if (!svg) throw new Error('\u201C' + name + '\u201D could not be written as SVG.');
      if (Math.abs(sz.scale - 1) > 1e-9) svg = svg.replace(/^(<svg[^>]*?) width="[^"]*" height="[^"]*"/, '$1 width="' + fx(sz.bw * sz.scale, 3) + '" height="' + fx(sz.bh * sz.scale, 3) + '"');
      return {blob: new Blob([svg], {type: MIME.svg}), w: Math.round(sz.bw * sz.scale), h: Math.round(sz.bh * sz.scale), text: svg};
    }
    if (!sz.ok) throw TooBig(name, sz);
    const cv = R().toCanvas(id, sz.scale, {bounds: mode, bg: row.fmt === 'jpg' ? pageBg(id) : undefined});
    if (cv.width !== sz.w || cv.height !== sz.h) { if (num(cv.hdScale, sz.scale) < sz.scale - 1e-9) throw TooBig(name, sz); }
    const blob = await canvasBlob(cv, MIME[row.fmt], row.fmt === 'jpg' ? 0.92 : undefined);
    return {blob: blob, w: cv.width, h: cv.height};
  }
  /* a PDF page of one node: its size in points (1 design unit = 1 point) and its picture, a JPEG at 2x (less when 2x is too big) */
  async function pdfPage(id, outer) {
    await R().ready(id, 8000);
    const mode = boundsMode(id, outer), b = boxOf(id, mode), scale = Math.max(0.01, Math.min(2, maxScaleFor(b)));
    const cv = R().toCanvas(id, scale, {bounds: mode, bg: pageBg(id)});
    const blob = await canvasBlob(cv, 'image/jpeg', 0.92);
    return {w: b.w, h: b.h, jpeg: await blobBytes(blob), scale: scale};
  }

  /* the files a run will make. items: [{id, row}] -> [{id, row, name (file name), w, h, tooBig, max}], names unique */
  function plan(items, opts) {
    opts = opts || {};
    const out = [], used = new Map(), many = items.length > 1;
    for (const it of items) {
      const n = node(it.id);
      if (!n) continue;
      const row = cleanRow(it.row), sz = sizeFor(it.id, row, opts.outer), raster = row.fmt === 'png' || row.fmt === 'jpg';
      let base = safeName(n.name || TYPE_LABEL[n.type] || 'Layer', many) + safeSuffix(row.suffix), file = base + '.' + row.fmt, k = 1;
      while (used.has(file.toLowerCase())) file = base + '-' + (++k) + '.' + row.fmt;
      used.set(file.toLowerCase(), 1);
      const pdfSize = row.fmt === 'pdf';
      out.push({id: it.id, row: row, name: file, layer: n.name || TYPE_LABEL[n.type] || 'Layer', w: pdfSize ? Math.round(sz.bw) : raster ? sz.w : Math.round(sz.bw * sz.scale), h: pdfSize ? Math.round(sz.bh) : raster ? sz.h : Math.round(sz.bh * sz.scale),
        unit: pdfSize ? 'pt' : 'px', tooBig: raster && !sz.ok, max: sz.max});
    }
    return out;
  }
  function download(blob, name) {
    const url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url; a.download = name; a.rel = 'noopener'; a.style.display = 'none';
    document.body.appendChild(a); a.click();
    setTimeout(() => { if (a.parentNode) a.parentNode.removeChild(a); URL.revokeObjectURL(url); }, 60000);
  }
  /* run a plan: {files: [{name, blob}], failed: [{name, error}]}. onStep(i, total, name) between files. */
  async function runPlan(list, opts) {
    opts = opts || {};
    const files = [], failed = [];
    for (let i = 0; i < list.length; i++) {
      const p = list[i];
      if (opts.onStep) opts.onStep(i, list.length, p.name);
      await tick();
      try { const r = await renderOne(p.id, p.row, opts); files.push({name: p.name, blob: r.blob, w: r.w, h: r.h}); }
      catch (e) { failed.push({name: p.name, error: (e && e.message) || String(e), tooBig: !!(e && e.tooBig), max: e && e.max}); }
    }
    return {files: files, failed: failed};
  }
  /* ONE PDF, a page per node */
  async function combinedPdf(ids, opts) {
    const pages = [];
    for (let i = 0; i < ids.length; i++) { if (opts && opts.onStep) opts.onStep(i, ids.length, 'page ' + (i + 1)); await tick(); if (node(ids[i])) pages.push(await pdfPage(ids[i], opts && opts.outer)); }
    return pdf(pages, {title: (opts && opts.title) || fileName()});
  }
  /* hand the result to the person: one file as it is, several in one ZIP */
  async function deliver(files, zipBase) {
    if (!files.length) return null;
    if (files.length === 1) { const one = files[0].name.split('/').pop(); download(files[0].blob, one); return one; }
    const data = [];
    for (const f of files) data.push({name: f.name, data: await blobBytes(f.blob)});
    const name = safeName(zipBase || fileName()) + '.zip';
    download(zip(data), name);
    return name;
  }
  /* the quick path: these nodes with their own rows (PNG at 1x when a node has none) */
  function itemsFor(ids, fallback) {
    const items = [];
    for (const id of ids) { if (!node(id)) continue; const rows = rowsOf(id); if (rows.length) for (const r of rows) items.push({id: id, row: r}); else items.push({id: id, row: cleanRow(fallback || {fmt: 'png', scale: 1})}); }
    return items;
  }
  let busy = false;
  async function exportNow(ids, fallback, opts) {
    if (busy) { toast('An export is still running.'); return null; }
    const list = plan(itemsFor(ids, fallback), opts);
    if (!list.length) { toast('Select a layer to export.'); return null; }
    busy = true;
    try {
      const res = await runPlan(list, opts);
      const name = await deliver(res.files, list.length > 1 && ids.length === 1 ? (node(ids[0]) || {}).name : fileName());
      if (res.failed.length) toast(res.failed[0].error + (res.failed.length > 1 ? ' (' + (res.failed.length - 1) + ' more could not be made.)' : ''), true);
      else if (name) toast(res.files.length === 1 ? 'Exported ' + name + '.' : 'Exported ' + res.files.length + ' files in ' + name + '.');
      return res;
    } catch (e) { toast((e && e.message) || 'The export did not work.', true); return null; }
    finally { busy = false; }
  }

  /* ================================================================ the Export section of the Design panel */
  const sec = {el: null, ids: [], sig: '', timer: 0, run: 0};
  function ib(icon, title, run, cls) { const b = h('button', {class: 'hd-ib' + (cls ? ' ' + cls : ''), type: 'button', title: title, 'aria-label': title}, UI().icon(icon)); if (run) b.addEventListener('click', run); return b; }
  function secSig(ids) { return ids.join(',') + '|' + canEdit() + '|' + ids.slice(0, 40).map(id => JSON.stringify(P(id, 'exports') || [])).join(';') + '|' + (ids.length === 1 ? String((node(ids[0]) || {}).name) : ''); }
  function setRows(ids, rows) {
    if (!canEdit()) return;
    S().tx('Export settings', () => { for (const id of ids) if (node(id)) S().set(id, {exports: rows.length ? rows.map(r => Object.assign({}, r)) : null}); });
  }
  const SIZE_PRESETS = ['0.5x', '0.75x', '1x', '1.5x', '2x', '3x', '4x', '512w', '1080w', '512h'];
  function sizeField(get, set, disabled) {
    const inp = h('input', {class: 'hd-in', type: 'text', value: sizeLabel(get()), 'aria-label': 'Size', spellcheck: 'false', autocomplete: 'off', disabled: !!disabled,
      title: 'Size: 2x, 0.5x, 512w (pixels wide) or 300h (pixels high)'});
    const commit = () => { const v = parseSize(inp.value); if (!v) { inp.value = sizeLabel(get()); return; } const cur = get(); if (sizeLabel(Object.assign({scale: 1}, v)) !== sizeLabel(cur)) set(v); inp.value = sizeLabel(get()); };
    inp.addEventListener('change', commit);
    inp.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); commit(); inp.select(); } else if (ev.key === 'Escape') { ev.preventDefault(); ev.stopPropagation(); inp.value = sizeLabel(get()); inp.blur(); } });
    inp.addEventListener('focus', () => setTimeout(() => { if (document.activeElement === inp) inp.select(); }, 0));
    const more = ib('down', 'Common sizes', ev => UI().menu(ev.currentTarget, SIZE_PRESETS.map(p => ({label: p, checked: sizeLabel(get()) === p ? true : undefined, run: () => { set(parseSize(p)); inp.value = sizeLabel(get()); }})), {label: 'Sizes'}), 'sm');
    more.disabled = !!disabled;
    return h('div', {class: 'hdx-size'}, inp, more);
  }
  function fmtSelect(get, set, disabled) {
    const el = h('select', {class: 'hd-sel hdx-fmt', 'aria-label': 'Format', title: 'Format', disabled: !!disabled});
    for (const f of FORMATS) el.appendChild(h('option', {value: f[0], text: f[1]}));
    el.value = get(); el.addEventListener('change', () => set(el.value));
    return el;
  }
  function withSize(row, v) { const out = {fmt: row.fmt, scale: v.scale === undefined ? 1 : v.scale, suffix: row.suffix}; if (v.w) out.w = v.w; if (v.h) out.h = v.h; return out; }
  function secRender() {
    const el = sec.el;
    if (!el) return;
    const ids = sec.ids.filter(id => node(id));
    clear(el); sec.sig = secSig(ids);
    if (!ids.length) return;
    const edit = canEdit(), rows = rowsOf(ids[0]), n0 = node(ids[0]);
    const differ = ids.some(id => JSON.stringify(rowsOf(id)) !== JSON.stringify(rows));
    const change = fn => { const next = rows.map(r => Object.assign({}, r)); fn(next); setRows(ids, next); secRender(); };
    if (differ) {
      el.appendChild(h('p', {class: 'hd-note', text: 'These layers have different export settings.'}));
      if (edit) el.appendChild(h('button', {class: 'hd-linkbtn', type: 'button', text: 'Use the first layer\u2019s settings for all', on: {click: () => { setRows(ids, rows); secRender(); }}}));
    } else {
      rows.forEach((row, i) => {
        const suffix = h('input', {class: 'hd-in hdx-suffix', type: 'text', value: row.suffix, placeholder: 'Suffix', 'aria-label': 'File name suffix', title: 'Added to the file name, for example @2x', spellcheck: 'false', autocomplete: 'off', maxlength: '24', disabled: !edit});
        suffix.addEventListener('change', () => { if (suffix.value !== row.suffix) change(a => { a[i].suffix = safeSuffix(suffix.value); }); });
        suffix.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); suffix.blur(); } });
        const rm = ib('minus', 'Remove this export', () => change(a => { a.splice(i, 1); }), 'sm'); rm.disabled = !edit;
        el.appendChild(h('div', {class: 'hd-row hdx-row', 'data-i': String(i)},
          sizeField(() => rows[i], v => change(a => { a[i] = withSize(a[i], v); }), !edit), suffix,
          fmtSelect(() => row.fmt, v => change(a => { a[i].fmt = v; }), !edit), rm));
      });
      if (edit) el.appendChild(h('button', {class: 'hd-linkbtn hdx-add', type: 'button', text: rows.length ? 'Add another size' : 'Add an export setting', on: {click: () => change(a => {
        const k = a.length; a.push(k === 0 ? {fmt: 'png', scale: 1, suffix: ''} : {fmt: a[k - 1].fmt, scale: Math.min(4, k + 1), suffix: '@' + Math.min(4, k + 1) + 'x'}); })}}));
    }
    const prev = h('div', {class: 'hdx-prev', 'aria-hidden': 'true'}), cap = h('div', {class: 'hdx-cap'});
    el.appendChild(h('div', {class: 'hdx-prevwrap'}, prev, cap));
    const label = ids.length === 1 ? 'Export ' + (n0.name || TYPE_LABEL[n0.type] || 'layer') : 'Export ' + ids.length + ' layers';
    const go = h('button', {class: 'hd-btn pri hdx-go', type: 'button', title: label, on: {click: () => { go.disabled = true; exportNow(ids).then(() => { go.disabled = false; }); }}}, h('span', {class: 'hdx-golab', text: label}));
    el.appendChild(go);
    sec.prev = prev; sec.cap = cap;
    schedulePreview(60);
  }
  function schedulePreview(ms) { clearTimeout(sec.timer); sec.timer = setTimeout(drawPreview, ms); }
  async function drawPreview() {
    const prev = sec.prev, cap = sec.cap, ids = sec.ids.filter(id => node(id));
    if (!prev || !prev.isConnected || !ids.length) return;
    const id = ids[0], my = ++sec.run, rows = rowsOf(id), row = rows[0] || {fmt: 'png', scale: 1, suffix: ''};
    try {
      await R().ready(id, 1500);
      if (my !== sec.run || !node(id) || !prev.isConnected) return;
      const mode = boundsMode(id), b = boxOf(id, mode), dpr = Math.min(2, window.devicePixelRatio || 1), k = Math.min(232 / b.w, 120 / b.h, 4);
      const cv = R().toCanvas(id, Math.max(0.005, k * dpr), {bounds: mode});
      cv.style.width = Math.max(1, Math.round(b.w * k)) + 'px'; cv.style.height = Math.max(1, Math.round(b.h * k)) + 'px'; cv.className = 'hdx-prevcv';
      clear(prev).appendChild(cv);
      const sz = sizeFor(id, row);
      cap.textContent = (row.fmt === 'pdf' ? fx(sz.bw, 1) + ' \u00D7 ' + fx(sz.bh, 1) + ' pt' : commas(row.fmt === 'svg' ? Math.round(sz.bw * sz.scale) : sz.w) + ' \u00D7 ' + commas(row.fmt === 'svg' ? Math.round(sz.bh * sz.scale) : sz.h) + ' px') +
        ' \u00B7 ' + row.fmt.toUpperCase() + (ids.length > 1 ? ' \u00B7 and ' + (ids.length - 1) + ' more' : rows.length > 1 ? ' \u00B7 ' + rows.length + ' files' : '');
      cap.classList.toggle('bad', (row.fmt === 'png' || row.fmt === 'jpg') && !sz.ok);
      if ((row.fmt === 'png' || row.fmt === 'jpg') && !sz.ok) cap.textContent += ' \u00B7 too large, use ' + fx(sz.max, 2) + 'x or less';
    } catch (e) { if (my === sec.run) clear(prev); }
  }
  function exportSection(el, ids) {
    sec.el = el; sec.ids = (ids || []).slice();
    secRender();
    const st = UI().state;
    if (st && Array.isArray(st.syncs)) st.syncs.push(() => { if (sec.el === el && el.isConnected && secSig(sec.ids.filter(id => node(id))) !== sec.sig) secRender(); });
  }

  /* ================================================================ the Export dialog (top bar, Ctrl+Shift+E) */
  function exportDialog(ids) {
    ids = (ids || []).filter(id => node(id));
    const page = HD.sel.page, frames = S().children(page).filter(id => CONT[typeOf(id)] && P(id, 'visible') !== false);
    if (!ids.length && !frames.length) { toast('There is nothing to export on this page yet. Draw a frame first.'); return null; }
    const fmt0 = lsGet('hd.export.fmt', 'png');
    const st = {scope: ids.length ? 'sel' : 'frames', row: {fmt: FMT_OK[fmt0] ? fmt0 : 'png', scale: 1, suffix: ''}, own: true, onePdf: true, outer: false, over: {}, running: false};
    const listEl = h('div', {class: 'hdx-list', role: 'list', 'aria-label': 'Files that will be made'}), sumEl = h('p', {class: 'hdx-sum', role: 'status'}), noteEl = h('p', {class: 'hd-note hdx-dnote'});
    const optsEl = h('div', {class: 'hdx-opts'}), scopeEl = h('div', {class: 'hd-seg hdx-scope', role: 'radiogroup', 'aria-label': 'What to export'});
    const fixAll = h('button', {class: 'hd-linkbtn', type: 'button', text: 'Use the largest size that works', hidden: true});
    const cancel = h('button', {class: 'hd-btn', type: 'button', text: 'Cancel', on: {click: () => UI().closeModal()}});
    const go = h('button', {class: 'hd-btn pri', type: 'button', text: 'Export'});
    const targets = () => (st.scope === 'sel' ? ids : frames).filter(id => node(id));
    const anyOwn = () => targets().some(id => rowsOf(id).length > 0);
    function items() {
      const t = targets(), row = cleanRow(st.row);
      const list = st.own && anyOwn() ? itemsFor(t, row) : t.map(id => ({id: id, row: row}));
      return list.map((it, i) => (st.over[it.id + '#' + i] ? {id: it.id, row: Object.assign({}, it.row, {scale: st.over[it.id + '#' + i], w: undefined, h: undefined})} : it));
    }
    const combined = list => st.onePdf && list.length > 1 && list.every(p => p.row.fmt === 'pdf');
    function paint() {
      clear(scopeEl);
      for (const o of [['sel', 'Selection', ids.length], ['frames', 'All frames on this page', frames.length]]) {
        const b = h('button', {type: 'button', class: 'hd-segb' + (st.scope === o[0] ? ' on' : ''), role: 'radio', 'aria-checked': String(st.scope === o[0]), text: o[1] + ' (' + o[2] + ')', disabled: !o[2] || st.running,
          on: {click: () => { st.scope = o[0]; st.over = {}; paint(); }}});
        scopeEl.appendChild(b);
      }
      clear(optsEl);
      const check = (label, key, title) => { const c = h('input', {type: 'checkbox', checked: !!st[key], disabled: st.running}); c.addEventListener('change', () => { st[key] = c.checked; st.over = {}; paint(); }); return h('label', {class: 'hd-check', title: title || label}, c, h('span', {text: label})); };
      if (anyOwn()) optsEl.appendChild(check('Use each layer\u2019s own export settings', 'own', 'Layers that have export settings keep them; the others use the format above.'));
      const list = plan(items(), {outer: st.outer});
      if (list.length > 1 && list.every(p => p.row.fmt === 'pdf')) optsEl.appendChild(check('One PDF with a page for each', 'onePdf'));
      if (targets().some(id => CONT[typeOf(id)])) optsEl.appendChild(check('Keep shadows that reach outside a frame', 'outer', 'Off: a frame is exported at exactly its own size.'));
      clear(listEl);
      const one = combined(list), bad = list.filter(p => p.tooBig && !one);
      if (one) listEl.appendChild(h('div', {class: 'hdx-item', role: 'listitem'}, h('span', {class: 'hdx-iname', text: safeName(fileName()) + '.pdf'}), h('span', {class: 'hdx-isize', text: list.length + ' pages'})));
      else list.slice(0, 200).forEach((p, i) => {
        const line = h('div', {class: 'hdx-item' + (p.tooBig ? ' bad' : ''), role: 'listitem'}, h('span', {class: 'hdx-iname', text: p.name, title: p.name}),
          h('span', {class: 'hdx-isize', text: (p.tooBig ? 'Too large: ' : '') + commas(p.w) + ' \u00D7 ' + commas(p.h) + ' ' + p.unit}));
        if (p.tooBig) line.appendChild(h('button', {class: 'hd-linkbtn', type: 'button', text: 'Use ' + fx(p.max, 2) + 'x', disabled: st.running, on: {click: () => { st.over[p.id + '#' + i] = p.max; paint(); }}}));
        listEl.appendChild(line);
      });
      if (!one && list.length > 200) listEl.appendChild(h('div', {class: 'hdx-item', role: 'listitem'}, h('span', {class: 'hdx-iname', text: 'and ' + (list.length - 200) + ' more files'})));
      const zipName = safeName(fileName()) + '.zip';
      sumEl.textContent = !list.length ? 'Nothing to export.' : one ? '1 PDF with ' + list.length + ' pages.' : list.length === 1 ? '1 file: ' + list[0].name.split('/').pop() : list.length + ' files, packed in ' + zipName;
      const notes = [];
      if (list.some(p => p.row.fmt === 'pdf')) notes.push('A PDF page is a picture of the frame (JPEG at 2x) at its size in points: the text in it can not be selected.');
      if (list.some(p => p.row.fmt === 'jpg')) notes.push('JPG has no transparency: empty areas become white.');
      if (bad.length) notes.push(bad.length === 1 ? 'One file is larger than a browser can draw (' + commas(LIMIT_SIDE) + ' px a side). Choose a smaller size.' : bad.length + ' files are larger than a browser can draw (' + commas(LIMIT_SIDE) + ' px a side). Choose a smaller size.');
      noteEl.textContent = notes.join(' '); noteEl.hidden = !notes.length; noteEl.classList.toggle('bad', bad.length > 0);
      fixAll.hidden = bad.length < 2; fixAll.onclick = () => { list.forEach((p, i) => { if (p.tooBig) st.over[p.id + '#' + i] = p.max; }); paint(); };
      go.disabled = st.running || !list.length || bad.length > 0;
      go.textContent = st.running ? 'Exporting\u2026' : list.length > 1 && !one ? 'Export ' + list.length + ' files' : 'Export';
      cancel.textContent = st.running ? 'Close' : 'Cancel';
    }
    const fmtSel = fmtSelect(() => st.row.fmt, v => { st.row.fmt = v; lsSet('hd.export.fmt', v); st.over = {}; paint(); });
    const size = sizeField(() => st.row, v => { st.row = withSize(st.row, v); st.over = {}; paint(); });
    const suffix = h('input', {class: 'hd-in hdx-suffix', type: 'text', placeholder: 'Suffix', 'aria-label': 'File name suffix', spellcheck: 'false', autocomplete: 'off', maxlength: '24'});
    suffix.addEventListener('input', () => { st.row.suffix = safeSuffix(suffix.value); paint(); });
    go.addEventListener('click', async () => {
      const list = plan(items(), {outer: st.outer});
      if (!list.length || st.running || busy) return;
      st.running = true; busy = true; paint();
      try {
        let name;
        if (combined(list)) {
          const blob = await combinedPdf(list.map(p => p.id), {outer: st.outer, title: fileName(), onStep: (i, n) => { sumEl.textContent = 'Drawing page ' + (i + 1) + ' of ' + n + '\u2026'; }});
          name = safeName(fileName()) + '.pdf'; download(blob, name); toast('Exported ' + name + ' (' + list.length + ' pages).');
        } else {
          const res = await runPlan(list, {outer: st.outer, onStep: (i, n, f) => { sumEl.textContent = 'Making ' + (i + 1) + ' of ' + n + ': ' + f.split('/').pop() + '\u2026'; }});
          name = await deliver(res.files, fileName());
          if (res.failed.length) { toast(res.failed[0].error + (res.failed.length > 1 ? ' (' + (res.failed.length - 1) + ' more could not be made.)' : ''), true); st.running = false; busy = false; paint(); return; }
          toast(res.files.length === 1 ? 'Exported ' + name + '.' : 'Exported ' + res.files.length + ' files in ' + name + '.');
        }
        st.running = false; busy = false; UI().closeModal();
      } catch (e) { st.running = false; busy = false; toast((e && e.message) || 'The export did not work.', true); paint(); }
    });
    const box = UI().modal('hdx-dialog', 'Export', [
      h('div', {class: 'hd-sheethead'}, h('h2', {text: 'Export'}), ib('close', 'Close', () => UI().closeModal())),
      h('div', {class: 'hdx-dbody'}, scopeEl,
        h('div', {class: 'hdx-drow'}, h('label', {class: 'hdx-lab'}, h('span', {text: 'Format'}), fmtSel), h('label', {class: 'hdx-lab'}, h('span', {text: 'Size'}), size), h('label', {class: 'hdx-lab grow'}, h('span', {text: 'Suffix'}), suffix)),
        optsEl, h('h3', {class: 'hdx-h3', text: 'What will be made'}), listEl, noteEl, fixAll),
      h('div', {class: 'hdx-foot'}, sumEl, cancel, go)]);
    paint();
    go.focus({preventScroll: true});
    return box;
  }

  /* ================================================================ copy as PNG / SVG */
  function selTop(ids) { ids = (ids || (HD.sel.ids || [])).filter(id => node(id)); try { return U().topLevel(ids); } catch (e) { return ids; } }
  function worldBox(id) {
    const n = node(id), b = boxOf(id, boundsMode(id)), par = n && n.parent, pt = typeOf(par);
    if (!par || pt === 'PAGE' || pt === 'DOCUMENT') return b;
    const m = S().worldMatrix(par), c = [M.apply(m, b.x, b.y), M.apply(m, b.x + b.w, b.y), M.apply(m, b.x + b.w, b.y + b.h), M.apply(m, b.x, b.y + b.h)];
    const xs = c.map(p => p[0]), ys = c.map(p => p[1]), x0 = Math.min.apply(null, xs), y0 = Math.min.apply(null, ys);
    return {x: x0, y: y0, w: Math.max.apply(null, xs) - x0, h: Math.max.apply(null, ys) - y0};
  }
  /* the selection as ONE canvas: a single layer through toCanvas, several drawn where they lie on the page */
  async function selectionCanvas(ids, want) {
    for (const id of ids) await R().ready(id, 6000);
    if (ids.length === 1) { const mode = boundsMode(ids[0]), b = boxOf(ids[0], mode); return R().toCanvas(ids[0], Math.max(0.01, Math.min(want, maxScaleFor(b))), {bounds: mode}); }
    let u = null;
    for (const id of ids) u = M.rectUnion(u, worldBox(id));
    const scale = Math.max(0.01, Math.min(want, maxScaleFor(u))), cv = document.createElement('canvas');
    cv.width = px(u.w * scale); cv.height = px(u.h * scale);
    const ctx = cv.getContext('2d');
    for (const id of ids) { ctx.setTransform(scale, 0, 0, scale, -u.x * scale, -u.y * scale); R().drawNode(ctx, id, {world: true}); }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    return cv;
  }
  async function copyPng(ids) {
    ids = selTop(ids);
    if (!ids.length) { toast('Select a layer to copy as a picture.'); return false; }
    if (!navigator.clipboard || !navigator.clipboard.write || typeof window.ClipboardItem !== 'function') { toast('This browser can not copy a picture. Use Export instead.', true); return false; }
    let size = '';
    const make = selectionCanvas(ids, 2).then(cv => { size = commas(cv.width) + ' \u00D7 ' + commas(cv.height) + ' px'; return canvasBlob(cv, 'image/png'); });
    try { await navigator.clipboard.write([new window.ClipboardItem({'image/png': make})]); toast('Copied as PNG (' + size + ', 2x).'); return true; }
    catch (e) { toast('The picture could not be copied: the browser did not allow it.', true); return false; }
  }
  function selectionSvg(ids) {
    if (ids.length === 1) return R().toSVG(ids[0], {bounds: boundsMode(ids[0])});
    let u = null; const boxes = ids.map(id => worldBox(id));
    for (const b of boxes) u = M.rectUnion(u, b);
    let body = '';
    ids.forEach((id, i) => { const s = R().toSVG(id, {bounds: boundsMode(id)}); if (s) body += s.replace(/^<svg /, '<svg x="' + fx(boxes[i].x - u.x, 3) + '" y="' + fx(boxes[i].y - u.y, 3) + '" '); });
    return '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="' + fx(u.w, 3) + '" height="' + fx(u.h, 3) + '" viewBox="0 0 ' + fx(u.w, 3) + ' ' + fx(u.h, 3) + '">' + body + '</svg>';
  }
  async function copyText(text, what) {
    try { if (navigator.clipboard && navigator.clipboard.writeText) { await navigator.clipboard.writeText(text); toast(what); return true; } } catch (e) { /* fall through to the old way */ }
    const ta = document.createElement('textarea'); ta.value = text; ta.setAttribute('readonly', ''); ta.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0';
    document.body.appendChild(ta); ta.select();
    let ok = false; try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    toast(ok ? what : 'The browser did not allow copying.', !ok);
    return ok;
  }
  async function copySvg(ids) {
    ids = selTop(ids);
    if (!ids.length) { toast('Select a layer to copy as SVG.'); return false; }
    for (const id of ids) await R().ready(id, 6000);
    const svg = selectionSvg(ids);
    if (!svg) { toast('This selection could not be written as SVG.', true); return false; }
    return copyText(svg, 'Copied as SVG.');
  }

  /* ================================================================ SVG import: the reading half (pure, no document edits)
     The SVG is parsed into an INERT XML document. Only names, geometry and paint attributes are read from it; it is
     never put into the page, nothing in it runs, and no address in it is fetched (a picture is taken only from a
     data: address). Every element is flattened to "where it lands" - its whole transform chain - and then written as
     the simplest node that can show it: a rectangle / ellipse / line when the transform is a turn, a flip and a
     stretch; a VECTOR path with the transform baked in for everything else (skew, paths, polygons). */
  const SVG_NS = 'http://www.w3.org/2000/svg', XLINK = 'http://www.w3.org/1999/xlink';
  const SVG_MAX_NODES = 20000, SVG_MAX_CHARS = 20 * 1024 * 1024, SVG_MAX_DEPTH = 60, PATH_MAX = 180000, IMG_MAX = 10 * 1024 * 1024;
  const NEVER = {script: 1, foreignObject: 1, iframe: 1, audio: 1, video: 1, canvas: 1, set: 1, animate: 1, animateMotion: 1, animateTransform: 1, discard: 1, handler: 1, listener: 1};
  const QUIET = {defs: 1, title: 1, desc: 1, metadata: 1, style: 1, linearGradient: 1, radialGradient: 1, pattern: 1, clipPath: 1, mask: 1, marker: 1, filter: 1, symbol: 1, view: 1, cursor: 1, font: 1, 'font-face': 1, 'color-profile': 1};
  const INHERIT = ['fill', 'fill-opacity', 'fill-rule', 'stroke', 'stroke-width', 'stroke-opacity', 'stroke-linecap', 'stroke-linejoin', 'stroke-dasharray', 'color', 'visibility',
    'font-family', 'font-size', 'font-weight', 'font-style', 'letter-spacing', 'text-anchor', 'text-decoration', 'clip-rule', 'white-space'];
  const OWN = ['opacity', 'display', 'clip-path', 'mask', 'filter', 'transform', 'mix-blend-mode', 'stop-color', 'stop-opacity', 'mask-type'];
  const PRES = INHERIT.concat(OWN);
  const BLENDS = {multiply: 1, screen: 1, overlay: 1, darken: 1, lighten: 1, 'color-dodge': 1, 'color-burn': 1, 'hard-light': 1, 'soft-light': 1, difference: 1, exclusion: 1, hue: 1, saturation: 1, color: 1, luminosity: 1};

  /* any CSS colour -> {hex:'#RRGGBB', a} or null. The browser's own colour reader does the work (a canvas fillStyle is
     only ever a colour: nothing is loaded or run by setting it). */
  let colorCtx = null;
  const colorMemo = new Map();
  function parseColor(str) {
    const s = String(str === null || str === undefined ? '' : str).trim().toLowerCase();
    if (!s || s.length > 120 || s === 'none' || /url\(|var\(|image|gradient|expression|javascript/.test(s)) return null;
    if (colorMemo.has(s)) return colorMemo.get(s);
    let out = null;
    if (s === 'transparent') out = {hex: '#000000', a: 0};
    else {
      const m = /^#([0-9a-f]{3,8})$/.exec(s);
      if (m && (m[1].length === 3 || m[1].length === 4 || m[1].length === 6 || m[1].length === 8)) {
        let x = m[1]; if (x.length < 6) x = x.split('').map(c => c + c).join('');
        out = {hex: '#' + x.slice(0, 6).toUpperCase(), a: x.length === 8 ? parseInt(x.slice(6), 16) / 255 : 1};
      } else if (!m) {
        if (!colorCtx) colorCtx = document.createElement('canvas').getContext('2d');
        colorCtx.fillStyle = '#000000'; colorCtx.fillStyle = s; const a = colorCtx.fillStyle;
        colorCtx.fillStyle = '#ffffff'; colorCtx.fillStyle = s; const b = colorCtx.fillStyle;
        if (a === b) {
          const h6 = /^#([0-9a-f]{6})$/i.exec(a), rg = /^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:[\s,/]+([\d.]+))?\s*\)$/i.exec(a);
          if (h6) out = {hex: '#' + h6[1].toUpperCase(), a: 1};
          else if (rg) out = {hex: '#' + [rg[1], rg[2], rg[3]].map(v => ('0' + clamp(Math.round(+v), 0, 255).toString(16)).slice(-2)).join('').toUpperCase(), a: rg[4] === undefined ? 1 : clamp(+rg[4], 0, 1)};
        }
      }
    }
    if (colorMemo.size > 4000) colorMemo.clear();
    colorMemo.set(s, out);
    return out;
  }
  function unitPx(v, unit, ref, em) {
    switch (unit) {
      case '%': return v * (ref || 0) / 100;
      case 'pt': return v * 96 / 72; case 'pc': return v * 16; case 'mm': return v * 96 / 25.4; case 'cm': return v * 96 / 2.54; case 'in': return v * 96; case 'q': return v * 96 / 101.6;
      case 'em': case 'rem': return v * (em || 16); case 'ex': case 'ch': return v * (em || 16) / 2;
      default: return v;
    }
  }
  /* an SVG length -> design units. ref = what 100% means, d = the answer when it is missing or broken */
  function len(v, ref, d, em) {
    if (v === null || v === undefined) return d;
    const m = /^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?)\s*([a-z%]*)\s*$/i.exec(String(v));
    if (!m) return d;
    const out = unitPx(parseFloat(m[1]), m[2].toLowerCase(), ref, em);
    return isFinite(out) ? out : d;
  }
  function numbers(s) { const out = [], re = /[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?/gi; let m; s = String(s || ''); while ((m = re.exec(s)) && out.length < 400000) out.push(parseFloat(m[0])); return out; }
  function parseTransform(str) {
    let m = [1, 0, 0, 1, 0, 0];
    const re = /(matrix|translate[xy]?|scale[xy]?|rotate|skew[xy])\s*\(([^)]*)\)/gi;
    let t, guard = 0;
    str = String(str || '');
    while ((t = re.exec(str)) && guard++ < 64) {
      const f = t[1].toLowerCase(), a = numbers(t[2]), ang = v => (/rad/i.test(t[2]) ? v : /turn/i.test(t[2]) ? v * Math.PI * 2 : v * DEG);
      let k = null;
      if (f === 'matrix' && a.length >= 6) k = a.slice(0, 6);
      else if (f === 'translate' && a.length) k = [1, 0, 0, 1, a[0], a[1] || 0];
      else if (f === 'translatex' && a.length) k = [1, 0, 0, 1, a[0], 0];
      else if (f === 'translatey' && a.length) k = [1, 0, 0, 1, 0, a[0]];
      else if (f === 'scale' && a.length) k = [a[0], 0, 0, a.length > 1 ? a[1] : a[0], 0, 0];
      else if (f === 'scalex' && a.length) k = [a[0], 0, 0, 1, 0, 0];
      else if (f === 'scaley' && a.length) k = [1, 0, 0, a[0], 0, 0];
      else if (f === 'rotate' && a.length) { const r = ang(a[0]), c = Math.cos(r), s = Math.sin(r), cx = a.length > 2 ? a[1] : 0, cy = a.length > 2 ? a[2] : 0; k = [c, s, -s, c, cx - c * cx + s * cy, cy - s * cx - c * cy]; }
      else if (f === 'skewx' && a.length) k = [1, 0, Math.tan(ang(a[0])), 1, 0, 0];
      else if (f === 'skewy' && a.length) k = [1, Math.tan(ang(a[0])), 0, 1, 0, 0];
      if (k && k.every(isFinite)) m = M.mul(m, k);
    }
    return m;
  }
  /* what a 2 x 3 matrix does, as a node can say it: a turn (degrees), a stretch (sx, sy) and flips; ok = no skew */
  function decomp(m) {
    const a = m[0], b = m[1], c = m[2], d = m[3], det = a * d - b * c, sx = Math.hypot(a, b), sy = Math.hypot(c, d);
    if (!(Math.abs(det) > 1e-12) || !(sx > 0) || !(sy > 0) || !isFinite(det)) return null;
    let rot = Math.atan2(b, a) / DEG, flipH = false, flipV = det < 0;
    if (Math.abs(Math.abs(rot) - 180) < 1e-7) { rot = 0; flipH = true; flipV = !flipV; }
    if (Math.abs(rot) < 1e-9) rot = 0;
    return {ok: Math.abs(a * c + b * d) / (sx * sy) < 1e-6, rot: rot, sx: sx, sy: sy, flipH: flipH, flipV: flipV, s: Math.sqrt(Math.abs(det)), uniform: Math.abs(sx - sy) <= 1e-6 * Math.max(sx, sy)};
  }

  /* ---- path data -> absolute ['M',x,y] ['L',x,y] ['C',x1,y1,x2,y2,x,y] ['Z'] (arcs and quadratics become cubics) */
  function arcCubics(x1, y1, rx, ry, phiDeg, fa, fs, x2, y2, out) {
    rx = Math.abs(rx); ry = Math.abs(ry);
    if (!rx || !ry || (x1 === x2 && y1 === y2)) { if (x1 !== x2 || y1 !== y2) out.push(['L', x2, y2]); return; }
    const phi = phiDeg * DEG, cp = Math.cos(phi), sp = Math.sin(phi), dx = (x1 - x2) / 2, dy = (y1 - y2) / 2;
    const x1p = cp * dx + sp * dy, y1p = -sp * dx + cp * dy;
    const lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry);
    if (lam > 1) { const k = Math.sqrt(lam); rx *= k; ry *= k; }
    const rx2 = rx * rx, ry2 = ry * ry, den = rx2 * y1p * y1p + ry2 * x1p * x1p;
    let co = den ? Math.sqrt(Math.max(0, (rx2 * ry2 - den) / den)) : 0;
    if (fa === fs) co = -co;
    const cxp = co * rx * y1p / ry, cyp = -co * ry * x1p / rx, cx = cp * cxp - sp * cyp + (x1 + x2) / 2, cy = sp * cxp + cp * cyp + (y1 + y2) / 2;
    const ang = (ux, uy, vx, vy) => { const d = Math.hypot(ux, uy) * Math.hypot(vx, vy); if (!d) return 0; let a = Math.acos(clamp((ux * vx + uy * vy) / d, -1, 1)); if (ux * vy - uy * vx < 0) a = -a; return a; };
    const th1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry);
    let dth = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry);
    if (!fs && dth > 0) dth -= Math.PI * 2; else if (fs && dth < 0) dth += Math.PI * 2;
    const n = Math.max(1, Math.ceil(Math.abs(dth) / (Math.PI / 2) - 1e-9)), dd = dth / n, t = 4 / 3 * Math.tan(dd / 4);
    for (let i = 0; i < n; i++) {
      const a1 = th1 + i * dd, a2 = a1 + dd, c1 = Math.cos(a1), s1 = Math.sin(a1), c2 = Math.cos(a2), s2 = Math.sin(a2);
      const p1x = cx + cp * rx * c1 - sp * ry * s1, p1y = cy + sp * rx * c1 + cp * ry * s1, ex = cx + cp * rx * c2 - sp * ry * s2, ey = cy + sp * rx * c2 + cp * ry * s2;
      const d1x = -cp * rx * s1 - sp * ry * c1, d1y = -sp * rx * s1 + cp * ry * c1, d2x = -cp * rx * s2 - sp * ry * c2, d2y = -sp * rx * s2 + cp * ry * c2;
      out.push(['C', p1x + t * d1x, p1y + t * d1y, ex - t * d2x, ey - t * d2y, i === n - 1 ? x2 : ex, i === n - 1 ? y2 : ey]);
    }
  }
  function parsePathD(d) {
    const s = String(d || ''), n = s.length, out = [], NUM = /[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/y;
    let i = 0, cmd = '', cx = 0, cy = 0, sx = 0, sy = 0, lx = 0, ly = 0, lc = '';
    const ws = () => { while (i < n) { const c = s.charCodeAt(i); if (c === 32 || c === 44 || (c >= 9 && c <= 13)) i++; else break; } };
    const nx = () => { ws(); NUM.lastIndex = i; const m = NUM.exec(s); if (!m) return NaN; i = NUM.lastIndex; return parseFloat(m[0]); };
    const flag = () => { ws(); const c = s.charAt(i); if (c === '0' || c === '1') { i++; return c === '1' ? 1 : 0; } return NaN; };
    while (out.length < 400000) {
      ws(); if (i >= n) break;
      const ch = s.charAt(i);
      if (/[a-zA-Z]/.test(ch)) {
        if ('MmLlHhVvCcSsQqTtAaZz'.indexOf(ch) < 0) break;
        i++; cmd = ch;
        if (ch === 'Z' || ch === 'z') { out.push(['Z']); cx = sx; cy = sy; lc = 'Z'; cmd = ''; continue; }
      } else if (!cmd) break;
      const rel = cmd >= 'a', C = cmd.toUpperCase(), ox = rel ? cx : 0, oy = rel ? cy : 0;
      let a, b, c, e, x, y;
      if (C === 'M') { x = nx(); y = nx(); if (y !== y) break; cx = x + ox; cy = y + oy; sx = cx; sy = cy; out.push(['M', cx, cy]); cmd = rel ? 'l' : 'L'; }
      else if (C === 'L') { x = nx(); y = nx(); if (y !== y) break; cx = x + ox; cy = y + oy; out.push(['L', cx, cy]); }
      else if (C === 'H') { x = nx(); if (x !== x) break; cx = x + ox; out.push(['L', cx, cy]); }
      else if (C === 'V') { y = nx(); if (y !== y) break; cy = y + oy; out.push(['L', cx, cy]); }
      else if (C === 'C') { a = nx(); b = nx(); c = nx(); e = nx(); x = nx(); y = nx(); if (y !== y) break; out.push(['C', a + ox, b + oy, c + ox, e + oy, x + ox, y + oy]); lx = c + ox; ly = e + oy; cx = x + ox; cy = y + oy; }
      else if (C === 'S') { c = nx(); e = nx(); x = nx(); y = nx(); if (y !== y) break; const sm = lc === 'C' || lc === 'S'; out.push(['C', sm ? 2 * cx - lx : cx, sm ? 2 * cy - ly : cy, c + ox, e + oy, x + ox, y + oy]); lx = c + ox; ly = e + oy; cx = x + ox; cy = y + oy; }
      else if (C === 'Q') { a = nx(); b = nx(); x = nx(); y = nx(); if (y !== y) break; const qx = a + ox, qy = b + oy, ex = x + ox, ey = y + oy; out.push(['C', cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy), ex + 2 / 3 * (qx - ex), ey + 2 / 3 * (qy - ey), ex, ey]); lx = qx; ly = qy; cx = ex; cy = ey; }
      else if (C === 'T') { x = nx(); y = nx(); if (y !== y) break; const sm = lc === 'Q' || lc === 'T', qx = sm ? 2 * cx - lx : cx, qy = sm ? 2 * cy - ly : cy, ex = x + ox, ey = y + oy; out.push(['C', cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy), ex + 2 / 3 * (qx - ex), ey + 2 / 3 * (qy - ey), ex, ey]); lx = qx; ly = qy; cx = ex; cy = ey; }
      else if (C === 'A') { const rx = nx(), ry = nx(), ph = nx(), fa = flag(), fs = flag(); x = nx(); y = nx(); if (y !== y || fa !== fa || fs !== fs) break; arcCubics(cx, cy, rx, ry, ph, fa, fs, x + ox, y + oy, out); cx = x + ox; cy = y + oy; }
      lc = C;
    }
    while (out.length && out[0][0] !== 'M') out.shift();
    return out;
  }
  function rectSegs(x, y, w, hh, rx, ry) {
    if (!(rx > 0) || !(ry > 0)) return [['M', x, y], ['L', x + w, y], ['L', x + w, y + hh], ['L', x, y + hh], ['Z']];
    const k = 0.5522847498, kx = rx * k, ky = ry * k;
    return [['M', x + rx, y], ['L', x + w - rx, y], ['C', x + w - rx + kx, y, x + w, y + ry - ky, x + w, y + ry], ['L', x + w, y + hh - ry], ['C', x + w, y + hh - ry + ky, x + w - rx + kx, y + hh, x + w - rx, y + hh],
      ['L', x + rx, y + hh], ['C', x + rx - kx, y + hh, x, y + hh - ry + ky, x, y + hh - ry], ['L', x, y + ry], ['C', x, y + ry - ky, x + rx - kx, y, x + rx, y], ['Z']];
  }
  function ellipseSegs(cx, cy, rx, ry) {
    const k = 0.5522847498, kx = rx * k, ky = ry * k;
    return [['M', cx + rx, cy], ['C', cx + rx, cy + ky, cx + kx, cy + ry, cx, cy + ry], ['C', cx - kx, cy + ry, cx - rx, cy + ky, cx - rx, cy], ['C', cx - rx, cy - ky, cx - kx, cy - ry, cx, cy - ry], ['C', cx + kx, cy - ry, cx + rx, cy - ky, cx + rx, cy], ['Z']];
  }
  function segsBox(segs) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, px0 = 0, py0 = 0;
    const pt = (x, y) => { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; };
    for (const sg of segs) {
      if (sg[0] === 'Z') continue;
      if (sg[0] !== 'C') { px0 = sg[1]; py0 = sg[2]; pt(px0, py0); continue; }
      pt(sg[5], sg[6]);
      for (let k = 0; k < 2; k++) {
        const p0 = k ? py0 : px0, p1 = sg[1 + k], p2 = sg[3 + k], p3 = sg[5 + k], A = -p0 + 3 * p1 - 3 * p2 + p3, B = 2 * (p0 - 2 * p1 + p2), C = p1 - p0, ts = [];
        if (Math.abs(A) < 1e-12) { if (Math.abs(B) > 1e-12) ts.push(-C / B); } else { const disc = B * B - 4 * A * C; if (disc >= 0) { const sq = Math.sqrt(disc); ts.push((-B + sq) / (2 * A), (-B - sq) / (2 * A)); } }
        for (const t of ts) if (t > 0 && t < 1) {
          const u = 1 - t, v = u * u * u * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t * t * t * p3;
          if (k) { if (v < y0) y0 = v; if (v > y1) y1 = v; } else { if (v < x0) x0 = v; if (v > x1) x1 = v; }
        }
      }
      px0 = sg[5]; py0 = sg[6];
    }
    return x0 === Infinity ? null : {x: x0, y: y0, w: x1 - x0, h: y1 - y0};
  }
  function mapSegs(segs, m) {
    return segs.map(sg => { if (sg[0] === 'Z') return sg; const out = [sg[0]]; for (let i = 1; i < sg.length; i += 2) { const p = M.apply(m, sg[i], sg[i + 1]); out.push(p[0], p[1]); } return out; });
  }
  function segsD(segs, dx, dy, places) {
    const f = v => { const k = Math.pow(10, places), r = Math.round(v * k) / k; return String(r === 0 ? 0 : r); };
    let d = '';
    for (const sg of segs) {
      if (sg[0] === 'Z') { d += 'Z'; continue; }
      d += sg[0];
      for (let i = 1; i < sg.length; i += 2) d += (i > 1 ? ' ' : '') + f(sg[i] - dx) + ' ' + f(sg[i + 1] - dy);
    }
    return d;
  }

  /* ---- the reader */
  function svgRead(text, opts) {
    opts = opts || {};
    text = String(text === null || text === undefined ? '' : text).replace(/^\uFEFF/, '');
    if (text.length > SVG_MAX_CHARS) throw new Error('This SVG is over 20 MB, too big to import.');
    /* a file saved without its namespaces still opens: say them for it */
    text = text.replace(/<svg(?=[\s>])([^>]*)>/i, (all, attrs) => {
      let extra = '';
      if (!/\sxmlns\s*=/.test(attrs)) extra += ' xmlns="' + SVG_NS + '"';
      if (!/\sxmlns:xlink\s*=/.test(attrs) && /xlink:/.test(text)) extra += ' xmlns:xlink="' + XLINK + '"';
      return '<svg' + extra + attrs + '>';
    });
    let doc;
    try { doc = new DOMParser().parseFromString(text, 'image/svg+xml'); } catch (e) { doc = null; }
    const root = doc && doc.documentElement;
    if (!root || doc.getElementsByTagName('parsererror').length || root.localName !== 'svg' || root.namespaceURI !== SVG_NS) throw new Error('This file could not be read as an SVG picture.');
    const st = {count: 0, capped: false, left: {unsafe: 0, outside: 0, clip: 0, mask: 0, text: 0, other: 0}, ids: new Map(), rules: [], uploads: [], vw: 0, vh: 0, order: 0};
    for (const el of doc.querySelectorAll('[id]')) { const id = el.getAttribute('id'); if (id && !st.ids.has(id)) st.ids.set(id, el); }
    for (const sEl of doc.getElementsByTagNameNS(SVG_NS, 'style')) cssRules(sEl.textContent || '', st);
    for (const tag of Object.keys(NEVER)) st.left.unsafe += doc.getElementsByTagNameNS('*', tag).length;

    function cssDecls(text, into) {
      for (const part of String(text || '').split(';')) { const i = part.indexOf(':'); if (i < 1) continue; const k = part.slice(0, i).trim().toLowerCase(), v = part.slice(i + 1).replace(/!important/i, '').trim(); if (k && v && v.length < 4000) into[k] = v; }
      return into;
    }
    function cssRules(css, state) {
      css = String(css).replace(/\/\*[\s\S]*?\*\//g, '').replace(/<!--|-->/g, '');
      const re = /([^{}]+)\{([^{}]*)\}/g;
      let m, guard = 0;
      while ((m = re.exec(css)) && guard++ < 5000) {
        const decl = cssDecls(m[2], {});
        for (const raw of m[1].split(',')) {
          const sel = /^([a-zA-Z][\w-]*|\*)?((?:[.#][\w-]+)*)$/.exec(raw.trim());
          if (!sel || (!sel[1] && !sel[2])) continue;
          const cls = [], rule = {tag: sel[1] && sel[1] !== '*' ? sel[1] : '', id: '', cls: cls, decl: decl, spec: 0, order: state.order++};
          for (const p of sel[2].match(/[.#][\w-]+/g) || []) { if (p.charAt(0) === '#') rule.id = p.slice(1); else cls.push(p.slice(1)); }
          rule.spec = (rule.id ? 100 : 0) + cls.length * 10 + (rule.tag ? 1 : 0);
          state.rules.push(rule);
        }
      }
    }
    function ownStyle(el) {
      const own = {};
      for (const k of PRES) { const v = el.getAttribute(k); if (v !== null && v !== '') own[k] = v; }
      if (st.rules.length) {
        const cl = (el.getAttribute('class') || '').split(/\s+/).filter(Boolean), id = el.getAttribute('id') || '', hit = [];
        for (const r of st.rules) { if (r.tag && r.tag !== el.localName) continue; if (r.id && r.id !== id) continue; if (r.cls.length && !r.cls.every(c => cl.indexOf(c) >= 0)) continue; hit.push(r); }
        hit.sort((a, b) => a.spec - b.spec || a.order - b.order);
        for (const r of hit) Object.assign(own, r.decl);
      }
      const inline = el.getAttribute('style');
      if (inline) cssDecls(inline, own);
      return own;
    }
    function styleOf(el, parent) {
      const own = ownStyle(el), out = {};
      for (const k of INHERIT) { const v = own[k]; out[k] = v === undefined || v === 'inherit' ? parent[k] : v; }
      for (const k of OWN) { const v = own[k]; if (v !== undefined && v !== 'inherit') out[k] = v; }
      const pfs = num(parent.fs, 16), fsz = own['font-size'];
      out.fs = fsz === undefined || fsz === 'inherit' ? pfs : Math.max(0.1, len(fsz, pfs, pfs, pfs));
      return out;
    }
    function hrefOf(el) { return el.getAttribute('href') || el.getAttributeNS(XLINK, 'href') || ''; }
    function refId(v) { const m = /^\s*url\(\s*["']?#([^"')\s]+)["']?\s*\)/i.exec(String(v || '')); return m ? m[1] : ''; }
    function nameOf(el) {
      let nm = el.getAttribute('data-name') || el.getAttributeNS('http://www.inkscape.org/namespaces/inkscape', 'label') || '';
      if (!nm) for (const c of el.children) if (c.localName === 'title' && c.namespaceURI === SVG_NS) { nm = c.textContent || ''; break; }
      if (!nm) nm = el.getAttribute('id') || '';
      return nm.replace(/\s+/g, ' ').trim().slice(0, 120);
    }

    /* ---- paints */
    function gradientPaint(gel, geo, alpha) {
      const chain = [gel];
      for (let cur = gel, i = 0; i < 8; i++) { const r = hrefOf(cur), nx = r.charAt(0) === '#' ? st.ids.get(r.slice(1)) : null; if (!nx || chain.indexOf(nx) >= 0 || !/Gradient$/.test(nx.localName)) break; chain.push(nx); cur = nx; }
      const attr = name => { for (const g of chain) { const v = g.getAttribute(name); if (v !== null) return v; } return null; };
      let stopEls = [];
      for (const g of chain) { stopEls = Array.from(g.children).filter(c => c.localName === 'stop'); if (stopEls.length) break; }
      const stops = [];
      let last = 0;
      for (const s of stopEls.slice(0, 64)) {
        const o = ownStyle(s), offRaw = s.getAttribute('offset') || '0';
        const off = clamp(/%\s*$/.test(offRaw) ? parseFloat(offRaw) / 100 : parseFloat(offRaw) || 0, 0, 1), c = parseColor(o['stop-color'] === 'currentColor' ? geo.color : o['stop-color'] || '#000');
        last = Math.max(last, off);
        const op = clamp(num(parseFloat(o['stop-opacity']), 1), 0, 1) * (c ? c.a : 1);
        stops.push({pos: rnd(last, 4), color: c ? c.hex : '#000000', opacity: rnd(op, 4)});
      }
      if (!stops.length) return null;
      if (stops.length === 1) return {type: 'solid', color: stops[0].color, opacity: rnd(stops[0].opacity * alpha, 4), visible: true};
      const user = attr('gradientUnits') === 'userSpaceOnUse', gm = parseTransform(attr('gradientTransform') || ''), ub = geo.ubox || {x: 0, y: 0, w: 1, h: 1};
      const at = (x, y) => { let p = M.apply(gm, x, y); if (!user) p = [ub.x + p[0] * ub.w, ub.y + p[1] * ub.h]; const q = geo.toBox(p[0], p[1]); return [rnd(q[0], 5), rnd(q[1], 5)]; };
      const g = (name, d, ref) => { const v = attr(name); if (v === null) return user ? d * ref : d; return user ? len(v, ref, d * ref) : (/%\s*$/.test(v) ? parseFloat(v) / 100 : parseFloat(v)) || 0; };
      if (gel.localName === 'linearGradient') return {type: 'linear', stops: stops, from: at(g('x1', 0, st.vw), g('y1', 0, st.vh)), to: at(g('x2', 1, st.vw), g('y2', 0, st.vh)), opacity: rnd(alpha, 4), visible: true};
      const cx = g('cx', 0.5, st.vw), cy = g('cy', 0.5, st.vh), r = g('r', 0.5, Math.hypot(st.vw, st.vh) / Math.SQRT2);
      return {type: 'radial', stops: stops, from: at(cx, cy), to: at(cx + r, cy), opacity: rnd(alpha, 4), visible: true};
    }
    /* key = 'fill' | 'stroke'; geo = {ubox, toBox(x, y) -> 0..1 of the node box, color} */
    function paintsOf(style, key, geo) {
      let v = style[key];
      if (v === undefined) v = key === 'fill' ? '#000' : 'none';
      v = String(v).trim();
      const alpha = clamp(num(parseFloat(style[key + '-opacity']), 1), 0, 1);
      if (!v || v === 'none' || !(alpha > 0)) return [];
      const ref = refId(v);
      if (ref) {
        const el = st.ids.get(ref);
        if (el && (el.localName === 'linearGradient' || el.localName === 'radialGradient')) { const p = gradientPaint(el, geo, alpha); return p ? [p] : []; }
        v = v.replace(/^\s*url\([^)]*\)\s*/i, '').trim();              /* the fallback colour after the reference */
        if (el && el.localName === 'pattern' && !v) { st.left.other++; v = '#C8C8CE'; }
        if (!v || v === 'none') return [];
      }
      if (/^currentcolor$/i.test(v)) v = geo.color || '#000';
      const c = parseColor(v);
      if (!c || !(c.a * alpha > 0)) return [];
      return [{type: 'solid', color: c.hex, opacity: rnd(c.a * alpha, 4), visible: true}];
    }
    function strokeProps(style, geo, scale, into) {
      const strokes = paintsOf(style, 'stroke', geo);
      if (!strokes.length) return;
      const sw = len(style['stroke-width'], Math.hypot(st.vw, st.vh) / Math.SQRT2, 1, style.fs) * scale;
      if (!(sw > 0)) return;
      into.strokes = strokes; into.strokeWeight = rnd(sw, 3); into.strokeAlign = 'center';
      const cap = style['stroke-linecap'], join = style['stroke-linejoin'];
      if (cap === 'round' || cap === 'square') into.strokeCap = cap;
      if (join === 'round' || join === 'bevel') into.strokeJoin = join;
      const da = style['stroke-dasharray'];
      if (da && da !== 'none') { let d = numbers(da).map(x => Math.abs(x) * scale); if (d.length % 2) d = d.concat(d); if (d.length && d.length <= 16 && d.some(x => x > 0)) into.dash = d.map(x => rnd(x, 3)); }
    }
    function effectsOf(style, scale) {
      const id = refId(style.filter), fel = id && st.ids.get(id);
      if (!fel || fel.localName !== 'filter') return null;
      const out = [];
      let cur = null, lastTag = '';
      const start = () => { if (!cur) cur = {x: 0, y: 0, blur: 0, spread: 0, color: '#000000', opacity: 1, inner: false, has: false}; return cur; };
      const done = kind => { if (cur && cur.has) out.push({type: kind || (cur.inner ? 'inner' : 'drop'), x: rnd(cur.x * scale, 3), y: rnd(cur.y * scale, 3), blur: rnd(cur.blur * scale, 3), spread: rnd(cur.spread * scale, 3), color: cur.color, opacity: rnd(cur.opacity, 4), visible: true}); cur = null; };
      const prims = Array.from(fel.children).slice(0, 80), sd = el => { const v = numbers(el.getAttribute('stdDeviation')); return v.length ? Math.max(v[0], v.length > 1 ? v[1] : v[0]) : 0; };
      for (const p of prims) {
        const tag = p.localName, input = p.getAttribute('in') || '';
        if (tag === 'feDropShadow') { const o = ownStyle(p), c = parseColor(p.getAttribute('flood-color') || o['flood-color'] || '#000'), fo = clamp(num(parseFloat(p.getAttribute('flood-opacity') || o['flood-opacity']), 1), 0, 1);
          out.push({type: 'drop', x: rnd(num(parseFloat(p.getAttribute('dx')), 2) * scale, 3), y: rnd(num(parseFloat(p.getAttribute('dy')), 2) * scale, 3), blur: rnd(sd(p) * 2 * scale, 3), spread: 0, color: c ? c.hex : '#000000', opacity: rnd(fo * (c ? c.a : 1), 4), visible: true}); }
        else if (tag === 'feGaussianBlur') { if (input === 'SourceGraphic' || input === 'all' || (prims.length === 1)) { if (sd(p) > 0) out.push({type: 'blur', blur: rnd(sd(p) * 2 * scale, 3), visible: true}); } else { start().blur = sd(p) * 2; cur.has = true; } }
        else if (tag === 'feOffset') { start().x = num(parseFloat(p.getAttribute('dx')), 0); cur.y = num(parseFloat(p.getAttribute('dy')), 0); cur.has = true; }
        else if (tag === 'feMorphology') { if (p.getAttribute('operator') === 'dilate') start().spread = numbers(p.getAttribute('radius'))[0] || 0; }
        else if (tag === 'feFlood') { const o = ownStyle(p), c = parseColor(p.getAttribute('flood-color') || o['flood-color'] || '#000'), fo = clamp(num(parseFloat(p.getAttribute('flood-opacity') || o['flood-opacity']), 1), 0, 1); if (fo > 0 || cur) { start().color = c ? c.hex : '#000000'; cur.opacity = fo * (c ? c.a : 1); } }
        else if (tag === 'feColorMatrix') { const v = numbers(p.getAttribute('values')); if (v.length === 20 && input !== 'SourceAlpha' && v[18] <= 1 && !v[0] && !v[1] && !v[2] && !v[5] && !v[6] && !v[7] && !v[10] && !v[11] && !v[12]) { start().color = '#' + [v[4], v[9], v[14]].map(x => ('0' + clamp(Math.round(x * 255), 0, 255).toString(16)).slice(-2)).join('').toUpperCase(); cur.opacity = clamp(v[18], 0, 1); } }
        else if (tag === 'feComposite') { const op = p.getAttribute('operator'); if (op === 'out' && lastTag === 'feFlood') start().inner = true; else if (op === 'arithmetic') start().inner = true; else if (op === 'in' && cur && cur.has) done(); }
        else if (tag === 'feBlend' || tag === 'feMerge') { const res = p.getAttribute('result') || ''; done(/innerShadow/i.test(res) ? 'inner' : /dropShadow/i.test(res) ? 'drop' : ''); }
        lastTag = tag;
      }
      done();
      return out.length ? out.slice(0, 8) : null;
    }

    /* ---- shapes. A spec is {type, x, y, w, h (where it lands, before its own turn), rot, flipH, flipV, props, kids} */
    function leaf(type, props) { st.count++; return {type: type, x: 0, y: 0, w: 0, h: 0, rot: 0, flipH: false, flipV: false, opacity: 1, props: props || {}, kids: null, name: ''}; }
    function vectorSpec(segs, m, style, extra) {
      const ub = segsBox(segs);
      if (!ub) return null;
      const moved = mapSegs(segs, m), bb = segsBox(moved), dec = decomp(m);
      if (!bb || !dec) return null;
      const s = leaf('VECTOR'), bw = bb.w || 1, bh = bb.h || 1;
      s.x = bb.x; s.y = bb.y; s.w = bb.w; s.h = bb.h;
      let d = segsD(moved, bb.x, bb.y, 3);
      if (d.length > PATH_MAX) d = segsD(moved, bb.x, bb.y, 1);
      if (d.length > PATH_MAX) { st.count--; st.left.other++; return null; }
      s.props.path = d;
      if (style['fill-rule'] === 'evenodd') s.props.fillRule = 'evenodd';
      const geo = {ubox: ub, color: style.color, toBox: (x, y) => { const q = M.apply(m, x, y); return [(q[0] - bb.x) / bw, (q[1] - bb.y) / bh]; }};
      s.props.fills = extra && extra.noFill ? [] : paintsOf(style, 'fill', geo);
      strokeProps(style, geo, dec.s, s.props);
      return s;
    }
    /* a box shape (RECT / ELLIPSE): kept as that node when the transform allows, else a path */
    function boxSpec(type, x, y, w, hh, rx, ry, m, style) {
      if (!(w > 0) || !(hh > 0)) return null;
      const dec = decomp(m);
      if (!dec) return null;
      const round = type === 'RECT' && rx > 0 && ry > 0;
      if (!dec.ok || (round && (Math.abs(rx - ry) > 1e-6 || !dec.uniform))) return vectorSpec(type === 'RECT' ? rectSegs(x, y, w, hh, rx, ry) : ellipseSegs(x + w / 2, y + hh / 2, w / 2, hh / 2), m, style);
      const s = leaf(type), c = M.apply(m, x + w / 2, y + hh / 2);
      s.w = w * dec.sx; s.h = hh * dec.sy; s.x = c[0] - s.w / 2; s.y = c[1] - s.h / 2; s.rot = dec.rot; s.flipH = dec.flipH; s.flipV = dec.flipV;
      if (round) s.props.radius = rnd(rx * dec.s, 3);
      const geo = {ubox: {x: x, y: y, w: w, h: hh}, color: style.color, toBox: (px0, py0) => [(px0 - x) / w, (py0 - y) / hh]};
      s.props.fills = paintsOf(style, 'fill', geo);
      strokeProps(style, geo, dec.s, s.props);
      return s;
    }
    function lineSpec(x1, y1, x2, y2, m, style) {
      const dec = decomp(m);
      if (!dec) return null;
      const a = M.apply(m, x1, y1), b = M.apply(m, x2, y2), L = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (!(L > 0)) return null;
      const ub = {x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 1, h: Math.abs(y2 - y1) || 1}, props = {};
      strokeProps(style, {ubox: ub, color: style.color, toBox: (px0, py0) => { const q = M.apply(m, px0, py0), t = ((q[0] - a[0]) * (b[0] - a[0]) + (q[1] - a[1]) * (b[1] - a[1])) / (L * L); return [t, 0.5]; }}, dec.s, props);
      if (!props.strokes) return null;
      const s = leaf('LINE', props);
      s.w = L; s.h = 0; s.x = (a[0] + b[0]) / 2 - L / 2; s.y = (a[1] + b[1]) / 2; s.rot = Math.atan2(b[1] - a[1], b[0] - a[0]) / DEG;
      if (Math.abs(s.rot) < 1e-9) s.rot = 0;
      delete props.strokeAlign;
      return s;
    }
    function imageSpec(el, m, style, ctx) {
      const href = hrefOf(el).trim();
      const du = /^data:(image\/(?:png|jpe?g|webp|gif))((?:;[^;,]*)*?)(;base64)?,([\s\S]*)$/i.exec(href);
      if (!du) { st.left.outside++; return null; }
      let bytes;
      try {
        if (du[3]) { const bin = atob(du[4].replace(/\s+/g, '')); if (bin.length > IMG_MAX) throw new Error('big'); bytes = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i); }
        else bytes = latin1(unescape(du[4]));
      } catch (e) { st.left.other++; return null; }
      const kind = sniff(bytes);
      if (!kind || bytes.length > IMG_MAX) { st.left.other++; return null; }
      const dec = decomp(m);
      if (!dec) return null;
      const x = len(el.getAttribute('x'), ctx.vw, 0), y = len(el.getAttribute('y'), ctx.vh, 0), w = len(el.getAttribute('width'), ctx.vw, 0), hh = len(el.getAttribute('height'), ctx.vh, 0);
      const par = (el.getAttribute('preserveAspectRatio') || '').trim(), fill = {type: 'image', hash: '', mode: /slice/.test(par) || /^none/.test(par) ? 'fill' : 'fit', opacity: 1, visible: true};
      const s = leaf('RECT', {fills: [fill]});
      s.isImage = true; s.name = 'Image';
      s.late = {x: x, y: y, w: w, h: hh, m: m, dec: dec};
      placeImageSpec(s, w > 0 ? w : 1, hh > 0 ? hh : 1);
      st.uploads.push({spec: s, fill: fill, blob: new Blob([bytes], {type: kind})});
      return s;
    }
    function fontOf(style) {
      const list = String(style['font-family'] || '').split(',').map(f => f.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
      const known = (UI() && UI().fonts) || [];
      for (const f of list) {
        const low = f.toLowerCase();
        for (const k of known) if (k[1].toLowerCase() === low) return k[1];
        if (SYSTEM_FONTS[low]) return SYSTEM_FONTS[low];
      }
      return 'Inter';
    }
    function textStyle(style, scale) {
      const wRaw = String(style['font-weight'] || '400').trim().toLowerCase();
      let weight = wRaw === 'bold' || wRaw === 'bolder' ? 700 : wRaw === 'lighter' ? 300 : parseInt(wRaw, 10) || 400;
      weight = clamp(Math.round(weight / 100) * 100, 100, 900);
      const deco = String(style['text-decoration'] || '');
      return {font: fontOf(style), fontSize: rnd(Math.max(0.5, style.fs * scale), 3), fontWeight: weight, italic: /italic|oblique/.test(style['font-style'] || ''),
        letterSpacing: rnd(len(style['letter-spacing'], 0, 0, style.fs) * scale, 3), decoration: /underline/.test(deco) ? 'underline' : /line-through/.test(deco) ? 'strike' : 'none'};
    }
    function textSpec(el, m, style, ctx) {
      const dec = decomp(m);
      if (!dec) return null;
      if (!dec.ok || !dec.uniform) st.left.text++;
      const s = dec.s, lines = [];
      const first = (v, ref, d) => { if (v === null) return d; const parts = String(v).trim().split(/[\s,]+/); return len(parts[0], ref, d, style.fs); };
      let cx = first(el.getAttribute('x'), ctx.vw, 0), cy = first(el.getAttribute('y'), ctx.vh, 0), brk = true, budget = 20000;
      cx += first(el.getAttribute('dx'), ctx.vw, 0); cy += first(el.getAttribute('dy'), ctx.vh, 0);
      const keep = el.getAttribute('xml:space') === 'preserve' || /pre/.test(style['white-space'] || '');
      const walk = (nd, stl, depth) => {
        for (const c of nd.childNodes) {
          if (c.nodeType === 3 || c.nodeType === 4) {
            let t = String(c.nodeValue || '');
            t = keep ? t.replace(/[\n\r\t]/g, ' ') : t.replace(/\s+/g, ' ');
            if (!t || budget <= 0) continue;
            t = t.slice(0, budget); budget -= t.length;
            if (brk || !lines.length) { lines.push({x: cx, y: cy, parts: [], anchor: stl['text-anchor'] || 'start'}); brk = false; }
            lines[lines.length - 1].parts.push({text: t, st: stl});
          } else if (c.nodeType === 1 && c.namespaceURI === SVG_NS && (c.localName === 'tspan' || c.localName === 'a' || c.localName === 'textPath') && depth < 12) {
            const cs = styleOf(c, stl);
            if (cs.display === 'none') continue;
            const ax = c.getAttribute('x'), ay = c.getAttribute('y'), adx = c.getAttribute('dx'), ady = c.getAttribute('dy');
            if (ax !== null) { cx = first(ax, ctx.vw, cx); brk = true; }
            if (ay !== null) { cy = first(ay, ctx.vh, cy); brk = true; }
            if (adx !== null) cx += first(adx, ctx.vw, 0);
            if (ady !== null) { const dy = first(ady, ctx.vh, 0); if (dy) { cy += dy; brk = true; } }
            walk(c, cs, depth + 1);
          }
        }
      };
      walk(el, style, 0);
      const real = [];
      for (const ln of lines) {
        if (!keep) { if (ln.parts.length) ln.parts[0].text = ln.parts[0].text.replace(/^\s+/, ''); if (ln.parts.length) ln.parts[ln.parts.length - 1].text = ln.parts[ln.parts.length - 1].text.replace(/\s+$/, ''); }
        ln.parts = ln.parts.filter(p => p.text);
        ln.text = ln.parts.map(p => p.text).join('');
        if (ln.text.trim()) real.push(ln);
      }
      if (!real.length) return null;
      const base = textStyle(real[0].parts[0].st, s);
      const fills = paintsOf(real[0].parts[0].st, 'fill', {ubox: {x: 0, y: 0, w: 1, h: 1}, color: style.color, toBox: (x, y) => [x, y]}).map(p => (p.type === 'solid' ? p : {type: 'solid', color: p.stops[0].color, opacity: p.opacity, visible: true}));
      const measure = (chars, lh) => { try { return LY().textLayout(Object.assign({type: 'TEXT', chars: chars, autoResize: 'wh', lineHeight: lh || 'auto', align: 'left'}, base)); } catch (e) { return null; } };
      for (const ln of real) { const lay = measure(ln.text); ln.w = lay && lay.lines[0] ? lay.lines[0].w / s : ln.text.length * base.fontSize * 0.5 / s; ln.base = lay && lay.lines[0] ? lay.lines[0].base / s : base.fontSize * 0.9 / s;
        ln.h = lay ? lay.h / s : base.fontSize * 1.2 / s; ln.left = ln.anchor === 'middle' ? ln.x - ln.w / 2 : ln.anchor === 'end' ? ln.x - ln.w : ln.x; }
      const one = (lns, align, lh) => {
        const sp = leaf('TEXT'), chars = lns.map(l => l.text).join('\n'), lay = measure(chars, lh ? rnd(lh * s, 3) : 'auto');
        const W = lay ? lay.w : Math.max.apply(null, lns.map(l => l.w)) * s, H = lay ? lay.h : lns.length * base.fontSize * 1.2, base0 = lay && lay.lines[0] ? lay.lines[0].base : base.fontSize * 0.9;
        const widest = Math.max.apply(null, lns.map(l => l.w));
        const left = align === 'center' ? lns[0].left + lns[0].w / 2 - W / s / 2 : align === 'right' ? lns[0].left + lns[0].w - W / s : Math.min.apply(null, lns.map(l => l.left));
        void widest;
        const top = lns[0].y - base0 / s, c = M.apply(m, left + W / s / 2, top + H / s / 2);
        sp.w = W; sp.h = H; sp.x = c[0] - W / 2; sp.y = c[1] - H / 2; sp.rot = dec.rot; sp.flipH = dec.flipH; sp.flipV = dec.flipV;
        Object.assign(sp.props, base, {chars: chars, autoResize: 'wh', fills: fills});
        if (base.decoration === 'none') delete sp.props.decoration;
        if (!base.letterSpacing) delete sp.props.letterSpacing;
        if (!base.italic) delete sp.props.italic;
        if (lh) sp.props.lineHeight = rnd(lh * s, 3);
        if (align !== 'left') sp.props.align = align;
        /* a part that looks different from the first one becomes a style run */
        const runs = [];
        let at = 0;
        lns.forEach((l, li) => { for (const p of l.parts) { const ts = textStyle(p.st, s), r = {};
          for (const k of ['font', 'fontSize', 'fontWeight', 'italic', 'decoration']) if (ts[k] !== base[k]) r[k] = ts[k];
          const pf = paintsOf(p.st, 'fill', {ubox: {x: 0, y: 0, w: 1, h: 1}, color: style.color, toBox: (x, y) => [x, y]}).filter(q => q.type === 'solid');
          if (pf.length && (!fills.length || pf[0].color !== fills[0].color || pf[0].opacity !== fills[0].opacity)) r.fills = pf;
          if (Object.keys(r).length && runs.length < 200) runs.push(Object.assign({s: at, e: at + p.text.length}, r));
          at += p.text.length; } if (li < lns.length - 1) at += 1; });
        if (runs.length) sp.props.runs = runs;
        sp.name = chars.replace(/\s+/g, ' ').trim().slice(0, 40);
        return sp;
      };
      if (real.length === 1) return one(real, real[0].anchor === 'middle' ? 'center' : real[0].anchor === 'end' ? 'right' : 'left', 0);
      /* several lines: one text layer when they are a paragraph (even line spacing and one common edge or centre) */
      const gaps = []; for (let i = 1; i < real.length; i++) gaps.push(real[i].y - real[i - 1].y);
      const even = gaps.every(g => g > 0 && Math.abs(g - gaps[0]) < 0.51), tol = 0.76;
      const sameBy = fn => real.every(l => Math.abs(fn(l) - fn(real[0])) < tol);
      const align = sameBy(l => l.left) ? 'left' : sameBy(l => l.left + l.w / 2) ? 'center' : sameBy(l => l.left + l.w) ? 'right' : '';
      if (even && align) return one(real, align, gaps[0]);
      const kids = real.map(l => one([l], 'left', 0));
      return {type: 'GROUP', kids: kids, props: {}, opacity: 1, name: kids[0].name, x: 0, y: 0, w: 0, h: 0, rot: 0};
    }

    /* ---- containers */
    function viewport(el, vw, vh) {
      const vb = numbers(el.getAttribute('viewBox'));
      if (vb.length < 4 || !(vb[2] > 0) || !(vb[3] > 0)) return {m: [1, 0, 0, 1, 0, 0], w: vw, h: vh};
      const par = (el.getAttribute('preserveAspectRatio') || 'xMidYMid meet').trim();
      let sx = vw / vb[2], sy = vh / vb[3], tx = 0, ty = 0;
      if (!/^none/.test(par)) {
        const k = /slice/.test(par) ? Math.max(sx, sy) : Math.min(sx, sy);
        tx = /xMid/.test(par) ? (vw - vb[2] * k) / 2 : /xMax/.test(par) ? vw - vb[2] * k : 0; ty = /YMid/.test(par) ? (vh - vb[3] * k) / 2 : /YMax/.test(par) ? vh - vb[3] * k : 0;
        if (!/x(Min|Mid|Max)Y(Min|Mid|Max)/.test(par)) { tx = (vw - vb[2] * k) / 2; ty = (vh - vb[3] * k) / 2; }
        sx = sy = k;
      }
      return {m: [sx, 0, 0, sy, tx - vb[0] * sx, ty - vb[1] * sy], w: vb[2], h: vb[3]};
    }
    function groupOf(kids, name) { return {type: 'GROUP', kids: kids, props: {}, opacity: 1, name: name || '', x: 0, y: 0, w: 0, h: 0, rot: 0}; }
    function childSpecs(el, ctx, m, style) {
      const kids = [];
      for (const c of el.children) { if (st.capped) break; const k = convert(c, {m: m, style: style, vw: ctx.vw, vh: ctx.vh, depth: ctx.depth + 1, uses: ctx.uses}); if (k) kids.push(k); }
      return mergeTwins(kids);
    }
    function upright(m) { return Math.abs(m[1]) < 1e-9 && Math.abs(m[2]) < 1e-9 && m[0] > 0 && m[3] > 0; }
    function clipFrame(kid, x, y, w, hh, radius, name) {
      st.count++;
      return {type: 'FRAME', kids: [kid], props: Object.assign({clip: true, fills: []}, radius ? {radius: radius} : null), opacity: 1, name: name || 'Clip', x: x, y: y, w: w, h: hh, rot: 0, fixed: true};
    }
    function sameGeo(a, b) {
      if (a.type !== b.type || a.kids || b.kids) return false;
      const near = (p, q) => Math.abs(p - q) < 0.011;
      if (!near(a.x, b.x) || !near(a.y, b.y) || !near(a.w, b.w) || !near(a.h, b.h) || !near(a.rot || 0, b.rot || 0) || !!a.flipH !== !!b.flipH || !!a.flipV !== !!b.flipV) return false;
      if (a.type === 'VECTOR') return a.props.path === b.props.path;
      return near(num(a.props.radius, 0), num(b.props.radius, 0));
    }
    /* a fill and a stroke drawn as two shapes on the same outline (how most tools, and Hoola, write SVG) -> one layer */
    function mergeTwins(kids) {
      const out = [];
      for (const b of kids) {
        const a = out[out.length - 1];
        if (a && !a.kids && !b.kids && a.type === b.type && !a.isImage && !b.isImage && a.opacity === 1 && b.opacity === 1 && !a.props.mask && !b.props.mask && !a.props.effects && !b.props.effects && !a.blend && !b.blend &&
            (a.type === 'RECT' || a.type === 'ELLIPSE' || a.type === 'VECTOR')) {
          const aF = (a.props.fills || []).length, aS = (a.props.strokes || []).length, bF = (b.props.fills || []).length, bS = (b.props.strokes || []).length;
          if (aF && !aS && bF && !bS && sameGeo(a, b)) { a.props.fills = a.props.fills.concat(b.props.fills); st.count--; continue; }
          if (aF && !aS && bS && !bF) {
            let align = '';
            if (sameGeo(a, b)) align = b.props.strokeAlign || 'center';
            else if (a.type !== 'VECTOR' && Math.abs((a.rot || 0) - (b.rot || 0)) < 0.011 && Math.abs(a.x + a.w / 2 - b.x - b.w / 2) < 0.011 && Math.abs(a.y + a.h / 2 - b.y - b.h / 2) < 0.011) {
              const dw = a.w - b.w, dh = a.h - b.h, sw = b.props.strokeWeight;
              if (Math.abs(dw - dh) < 0.021 && Math.abs(Math.abs(dw) - sw) < 0.021 && sw > 0) align = dw > 0 ? 'inside' : 'outside';
            }
            if (align) {
              for (const k of ['strokes', 'strokeWeight', 'strokeCap', 'strokeJoin', 'dash']) if (b.props[k] !== undefined) a.props[k] = b.props[k];
              a.props.strokeAlign = align; if (!a.name && b.name) a.name = b.name;
              st.count--; continue;
            }
          }
        }
        out.push(b);
      }
      return out;
    }
    /* a group that starts with a plain rectangle holding everything after it is a FRAME (its fill, its outline, its corners):
       how a frame with a background arrives from any tool, and what Hoola itself writes for one */
    function frameFromGroup(kids) {
      const a = kids[0];
      if (!a || a.kids || a.type !== 'RECT' || a.rot || a.flipH || a.flipV || a.opacity !== 1 || a.hidden || a.blend || a.props.mask || a.props.effects || !(a.props.fills || []).length || (a.late && a.late.auto)) return null;
      let rest = kids.slice(1), frame = a;
      const z = rest[rest.length - 1];
      if (z && !z.kids && z.type === 'RECT' && !(z.props.fills || []).length && (z.props.strokes || []).length) { const m2 = mergeTwins([Object.assign({}, a, {props: Object.assign({}, a.props)}), z]); if (m2.length === 1) { frame = m2[0]; st.count++; rest = rest.slice(0, -1); } }
      if (!rest.length) return null;
      for (const k of rest) { const b = specBox(k); if (!b || b.x0 < a.x - 0.51 || b.y0 < a.y - 0.51 || b.x1 > a.x + a.w + 0.51 || b.y1 > a.y + a.h + 0.51) return null; }
      /* the clip of that same box (a clipping frame written as a group) is this frame's own clip */
      if (rest.length === 1 && rest[0].type === 'FRAME' && rest[0].fixed && !(rest[0].props.fills || []).length && Math.abs(rest[0].x - a.x) < 0.011 && Math.abs(rest[0].y - a.y) < 0.011 && Math.abs(rest[0].w - a.w) < 0.011 && Math.abs(rest[0].h - a.h) < 0.011 && rest[0].opacity === 1) {
        const inner = rest[0].kids[0]; rest = inner.type === 'GROUP' && !inner.props.mask && inner.opacity === 1 && !inner.name ? inner.kids : [inner]; st.count--;
      }
      return {type: 'FRAME', kids: rest, props: Object.assign({clip: true}, frame.props), opacity: 1, name: a.name || '', x: a.x, y: a.y, w: a.w, h: a.h, rot: 0, fixed: true};
    }
    function specBox(s) {
      if (s.late && s.late.auto) return null;
      if (s.kids && s.type !== 'FRAME') { let r = null; for (const k of s.kids) { const b = specBox(k); if (!b) return null; r = r ? {x0: Math.min(r.x0, b.x0), y0: Math.min(r.y0, b.y0), x1: Math.max(r.x1, b.x1), y1: Math.max(r.y1, b.y1)} : b; } return r; }
      if (!s.rot) return {x0: s.x, y0: s.y, x1: s.x + s.w, y1: s.y + s.h};
      const c = Math.abs(Math.cos(s.rot * DEG)), sn = Math.abs(Math.sin(s.rot * DEG)), hw = (s.w * c + s.h * sn) / 2, hh2 = (s.w * sn + s.h * c) / 2, cx = s.x + s.w / 2, cy = s.y + s.h / 2;
      return {x0: cx - hw, y0: cy - hh2, x1: cx + hw, y1: cy + hh2};
    }
    function leaves(spec, out) { if (spec.kids) for (const k of spec.kids) leaves(k, out); else out.push(spec); return out; }
    function clipped(el, spec, m, style, ctx) {
      const cid = refId(style['clip-path']), cp = cid && st.ids.get(cid);
      if (cp && cp.localName === 'clipPath') {
        if (cp.getAttribute('clipPathUnits') === 'objectBoundingBox') st.left.clip++;
        else {
          const ct = cp.getAttribute('transform'), cm = ct ? M.mul(m, parseTransform(ct)) : m, shapes = [];
          for (const c of Array.from(cp.children).slice(0, 200)) { const k = convert(c, {m: cm, style: ROOT_STYLE, vw: ctx.vw, vh: ctx.vh, depth: ctx.depth + 1, uses: ctx.uses, plain: true}); if (k) leaves(k, shapes); }
          const shapesOk = shapes.filter(s => s.type !== 'TEXT' && s.type !== 'LINE' && !s.isImage);
          for (const s of shapesOk) { s.props.fills = [{type: 'solid', color: '#000000', opacity: 1, visible: true}]; delete s.props.strokes; delete s.props.strokeWeight; delete s.props.dash; s.opacity = 1; }
          st.count -= shapes.length - shapesOk.length;
          if (!shapesOk.length) { st.count -= countSpecs(spec); return null; }
          const one = shapesOk.length === 1 ? shapesOk[0] : null;
          if (one && !spec.kids && sameGeo(one, spec) && !(spec.props.fills || []).length && (spec.props.strokes || []).length) {
            spec.props.strokeAlign = 'inside'; spec.props.strokeWeight = rnd(spec.props.strokeWeight / 2, 3); st.count--; return spec;         /* a stroke kept inside its own outline */
          }
          if (one && spec.isImage && Math.abs(one.x - spec.x) < 0.51 && Math.abs(one.y - spec.y) < 0.51 && Math.abs(one.w - spec.w) < 0.51 && Math.abs(one.h - spec.h) < 0.51 && !spec.late.auto) {
            one.props.fills = spec.props.fills; one.isImage = true; one.late = null; one.name = spec.name; one.opacity = spec.opacity;       /* a picture cut to a shape = that shape with the picture as its fill */
            for (const u of st.uploads) if (u.spec === spec) u.spec = one;
            st.count--; return one;
          }
          if (one && one.type === 'RECT' && !one.rot && !one.flipH && !one.flipV) {
            st.count--; return clipFrame(spec, one.x, one.y, one.w, one.h, one.props.radius, spec.name);
          }
          const maskNode = one || groupOf(shapesOk, 'Mask');
          maskNode.props.mask = true; maskNode.name = 'Mask';
          spec = groupOf([maskNode, spec], spec.name);
        }
      }
      const mid = refId(style.mask), mk = mid && st.ids.get(mid);
      if (mk && mk.localName === 'mask') {
        const mstyle = ownStyle(mk);
        if (mstyle['mask-type'] === 'alpha' || mk.getAttribute('mask-type') === 'alpha') {
          const kids = [];
          for (const c of Array.from(mk.children).slice(0, 200)) { const k = convert(c, {m: m, style: ROOT_STYLE, vw: ctx.vw, vh: ctx.vh, depth: ctx.depth + 1, uses: ctx.uses}); if (k) kids.push(k); }
          const merged = mergeTwins(kids);
          if (merged.length) { const maskNode = merged.length === 1 ? merged[0] : groupOf(merged, 'Mask'); maskNode.props.mask = true; if (!maskNode.name) maskNode.name = 'Mask'; spec = groupOf([maskNode, spec], spec.name); }
        } else st.left.mask++;
      }
      return spec;
    }
    function countSpecs(spec) { let n = spec.kids && spec.type !== 'FRAME' ? 0 : 1; if (spec.kids) for (const k of spec.kids) n += countSpecs(k); return n; }

    function convert(el, ctx) {
      if (st.count >= SVG_MAX_NODES) { st.capped = true; return null; }
      if (el.namespaceURI !== SVG_NS || ctx.depth > SVG_MAX_DEPTH) return null;
      const tag = el.localName;
      if (NEVER[tag] || QUIET[tag]) return null;
      const style = styleOf(el, ctx.style);
      if (style.display === 'none') return null;
      const tr = el.getAttribute('transform') || (style.transform && style.transform !== 'none' ? style.transform : '');
      let m = tr ? M.mul(ctx.m, parseTransform(tr)) : ctx.m;
      const X = (name, d) => len(el.getAttribute(name), ctx.vw, d, style.fs), Y = (name, d) => len(el.getAttribute(name), ctx.vh, d, style.fs);
      let spec = null, explicit = nameOf(el);
      if (tag === 'g' || tag === 'a' || tag === 'switch') {
        const kids = childSpecs(el, ctx, m, style);
        if (!kids.length) return null;
        if (kids.length === 1) { spec = kids[0]; if (!explicit) explicit = spec.name; } else spec = frameFromGroup(kids) || groupOf(kids, '');
      } else if (tag === 'svg') {
        const x = X('x', 0), y = Y('y', 0), w = X('width', ctx.vw), hh = Y('height', ctx.vh);
        if (!(w > 0) || !(hh > 0)) return null;
        const base = M.mul(m, [1, 0, 0, 1, x, y]), vp = viewport(el, w, hh), kids = childSpecs(el, {m: base, style: style, vw: vp.w, vh: vp.h, depth: ctx.depth, uses: ctx.uses}, M.mul(base, vp.m), style);
        if (!kids.length) return null;
        const inner = kids.length === 1 ? kids[0] : groupOf(kids, '');
        if (upright(base) && (el.getAttribute('overflow') || 'hidden') !== 'visible') { const a = M.apply(base, 0, 0), b = M.apply(base, w, hh); spec = clipFrame(inner, a[0], a[1], b[0] - a[0], b[1] - a[1], 0, explicit || 'SVG'); } else spec = inner;
      } else if (tag === 'use') {
        const href = hrefOf(el).trim(), tid = href.charAt(0) === '#' ? href.slice(1) : '', target = tid ? st.ids.get(tid) : null;
        if (!target) { if (href && href.charAt(0) !== '#') st.left.outside++; return null; }
        if (ctx.uses.indexOf(tid) >= 0 || ctx.uses.length > 24 || target.contains(el)) return null;
        const um = M.mul(m, [1, 0, 0, 1, X('x', 0), Y('y', 0)]), sub = {m: um, style: style, vw: ctx.vw, vh: ctx.vh, depth: ctx.depth + 1, uses: ctx.uses.concat(tid)};
        if (target.localName === 'symbol' || target.localName === 'svg') {
          const w = X('width', len(target.getAttribute('width'), ctx.vw, ctx.vw)), hh = Y('height', len(target.getAttribute('height'), ctx.vh, ctx.vh)), vp = viewport(target, w, hh), tstyle = styleOf(target, style);
          const kids = childSpecs(target, {m: um, style: tstyle, vw: vp.w, vh: vp.h, depth: ctx.depth + 1, uses: sub.uses}, M.mul(um, vp.m), tstyle);
          if (!kids.length) return null;
          spec = kids.length === 1 ? kids[0] : groupOf(kids, nameOf(target));
        } else spec = convert(target, sub);
        if (!spec) return null;
        if (!explicit) explicit = spec.name;
      } else if (tag === 'rect') {
        const w = X('width', 0), hh = Y('height', 0);
        let rx = el.getAttribute('rx'), ry = el.getAttribute('ry');
        rx = rx === null || rx === 'auto' ? null : X('rx', 0); ry = ry === null || ry === 'auto' ? null : Y('ry', 0);
        if (rx === null) rx = ry; if (ry === null) ry = rx;
        spec = boxSpec('RECT', X('x', 0), Y('y', 0), w, hh, Math.min(Math.max(0, rx || 0), w / 2), Math.min(Math.max(0, ry || 0), hh / 2), m, style);
      } else if (tag === 'circle') { const r = X('r', 0); spec = boxSpec('ELLIPSE', X('cx', 0) - r, Y('cy', 0) - r, r * 2, r * 2, 0, 0, m, style); }
      else if (tag === 'ellipse') { const rx = X('rx', 0), ry = Y('ry', 0); spec = boxSpec('ELLIPSE', X('cx', 0) - rx, Y('cy', 0) - ry, rx * 2, ry * 2, 0, 0, m, style); }
      else if (tag === 'line') spec = lineSpec(X('x1', 0), Y('y1', 0), X('x2', 0), Y('y2', 0), m, style);
      else if (tag === 'polyline' || tag === 'polygon') {
        const p = numbers(el.getAttribute('points')), segs = [];
        for (let i = 0; i + 1 < p.length; i += 2) segs.push([i ? 'L' : 'M', p[i], p[i + 1]]);
        if (segs.length > 1) { if (tag === 'polygon') segs.push(['Z']); spec = vectorSpec(segs, m, style); }
      } else if (tag === 'path') { const segs = parsePathD(el.getAttribute('d')); if (segs.length > 1) spec = vectorSpec(segs, m, style); }
      else if (tag === 'image') spec = ctx.plain ? null : imageSpec(el, m, style, ctx);
      else if (tag === 'text') spec = textSpec(el, m, style, ctx);
      else { st.left.other++; return null; }
      if (!spec) return null;
      if (explicit) spec.name = explicit;
      const op = clamp(num(parseFloat(style.opacity), 1), 0, 1);
      if (op < 1) spec.opacity = (spec.opacity === undefined ? 1 : spec.opacity) * op;
      if (style.visibility === 'hidden' || style.visibility === 'collapse') spec.hidden = true;
      const bl = style['mix-blend-mode']; if (bl && BLENDS[bl]) spec.blend = bl;
      const dec = decomp(m), fxs = dec ? effectsOf(style, dec.s) : null;
      if (fxs) spec.props.effects = (spec.props.effects || []).concat(fxs).slice(0, 8);
      return clipped(el, spec, m, style, ctx);
    }

    /* ---- the root */
    let vw = len(root.getAttribute('width'), 0, NaN), vh = len(root.getAttribute('height'), 0, NaN);
    const vb0 = numbers(root.getAttribute('viewBox')), hasVb = vb0.length >= 4 && vb0[2] > 0 && vb0[3] > 0;
    if (/%\s*$/.test(root.getAttribute('width') || '')) vw = NaN;
    if (/%\s*$/.test(root.getAttribute('height') || '')) vh = NaN;
    if (!(vw > 0) && !(vh > 0)) { vw = hasVb ? vb0[2] : 300; vh = hasVb ? vb0[3] : 150; }
    else if (!(vw > 0)) vw = hasVb ? vh * vb0[2] / vb0[3] : 300;
    else if (!(vh > 0)) vh = hasVb ? vw * vb0[3] / vb0[2] : 150;
    vw = clamp(vw, 0.01, 1e6); vh = clamp(vh, 0.01, 1e6);
    const vp = viewport(root, vw, vh);
    st.vw = vp.w; st.vh = vp.h;
    const rootStyle = styleOf(root, ROOT_STYLE);
    const kids = childSpecs(root, {m: vp.m, style: rootStyle, vw: vp.w, vh: vp.h, depth: 0, uses: []}, vp.m, rootStyle);
    let title = '';
    for (const c of root.children) if (c.localName === 'title' && c.namespaceURI === SVG_NS) { title = (c.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80); break; }
    const rootName = String(opts.name || title || root.getAttribute('id') || '').slice(0, 120);
    let spec = {type: 'FRAME', kids: kids, props: {clip: true, fills: []}, opacity: clamp(num(parseFloat(rootStyle.opacity), 1), 0, 1), name: rootName || 'SVG', x: 0, y: 0, w: vw, h: vh, rot: 0, fixed: true};
    /* the picture is one frame that fills it (a frame exported from a design tool): that frame is the result, not a frame inside a frame */
    const only = kids.length === 1 ? kids[0] : kids.length > 1 ? frameFromGroup(kids) : null;                 /* ... or a background rectangle with everything on it */
    if (only && only.type === 'FRAME' && spec.opacity === 1 && Math.abs(only.x) < 0.011 && Math.abs(only.y) < 0.011 && Math.abs(only.w - vw) < 0.011 && Math.abs(only.h - vh) < 0.011) { spec = only; spec.name = rootName || only.name || 'SVG'; st.count--; }
    return {spec: spec, w: vw, h: vh, count: st.count + 1, capped: st.capped, left: st.left, uploads: st.uploads};
  }
  const ROOT_STYLE = {fs: 16, color: '#000000'};
  const SYSTEM_FONTS = {'arial': 'Arial', 'helvetica': 'Helvetica', 'times new roman': 'Times New Roman', 'times': 'Times', 'georgia': 'Georgia', 'courier new': 'Courier New', 'courier': 'Courier', 'verdana': 'Verdana',
    'tahoma': 'Tahoma', 'trebuchet ms': 'Trebuchet MS', 'segoe ui': 'Segoe UI', 'serif': 'serif', 'sans-serif': 'sans-serif', 'monospace': 'monospace', 'system-ui': 'system-ui'};
  function sniff(b) {
    if (b.length > 8 && b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4E && b[3] === 0x47) return 'image/png';
    if (b.length > 3 && b[0] === 0xFF && b[1] === 0xD8 && b[2] === 0xFF) return 'image/jpeg';
    if (b.length > 6 && b[0] === 0x47 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x38) return 'image/gif';
    if (b.length > 12 && b[0] === 0x52 && b[1] === 0x49 && b[2] === 0x46 && b[3] === 0x46 && b[8] === 0x57 && b[9] === 0x45 && b[10] === 0x42 && b[11] === 0x50) return 'image/webp';
    return '';
  }
  /* an <image>: its box in the picture's own space (w x h, natural size when the file gave none) -> where it lands */
  function placeImageSpec(s, w, hh) {
    const L = s.late, dec = L.dec, c = M.apply(L.m, L.x + w / 2, L.y + hh / 2);
    L.auto = !(L.w > 0) || !(L.h > 0);
    s.w = w * dec.sx; s.h = hh * dec.sy; s.x = c[0] - s.w / 2; s.y = c[1] - s.h / 2; s.rot = dec.rot; s.flipH = dec.flipH; s.flipV = dec.flipV;
  }

  /* ================================================================ SVG import: the writing half (one undo step) */
  const SPEC_NAME = {RECT: 'Rectangle', ELLIPSE: 'Ellipse', VECTOR: 'Vector', LINE: 'Line', GROUP: 'Group', FRAME: 'Frame', TEXT: 'Text'};
  function specExtent(s) {
    if (s.kids && s.type !== 'FRAME') { let r = null; for (const k of s.kids) { const b = specExtent(k); if (b) r = r ? {x0: Math.min(r.x0, b.x0), y0: Math.min(r.y0, b.y0), x1: Math.max(r.x1, b.x1), y1: Math.max(r.y1, b.y1)} : b; } return r; }
    if (!s.rot) return {x0: s.x, y0: s.y, x1: s.x + s.w, y1: s.y + s.h};
    const c = Math.abs(Math.cos(s.rot * DEG)), sn = Math.abs(Math.sin(s.rot * DEG)), hw = (s.w * c + s.h * sn) / 2, hh = (s.w * sn + s.h * c) / 2, cx = s.x + s.w / 2, cy = s.y + s.h / 2;
    return {x0: cx - hw, y0: cy - hh, x1: cx + hw, y1: cy + hh};
  }
  function buildSpec(spec, parentId, ox, oy, state) {
    if (state.n >= SVG_MAX_NODES) { state.capped = true; return null; }
    if (spec.type === 'GROUP') {
      const b = specExtent(spec);
      if (!b || !spec.kids.length) return null;
      spec.x = b.x0; spec.y = b.y0; spec.w = b.x1 - b.x0; spec.h = b.y1 - b.y0;
    }
    const p = Object.assign({}, spec.props);
    if (Array.isArray(p.fills) && !p.fills.length) delete p.fills;
    p.name = spec.name || SPEC_NAME[spec.type] || 'Layer';
    p.x = rnd(spec.x - ox, 3); p.y = rnd(spec.y - oy, 3); p.w = rnd(Math.max(0, spec.w), 3);
    if (spec.type !== 'LINE') p.h = rnd(Math.max(0, spec.h), 3);
    if (spec.rot && Math.abs(spec.rot) >= 0.005) p.rot = rnd(spec.rot, 2);
    if (typeof p.strokeWeight === 'number') p.strokeWeight = rnd(p.strokeWeight, 2);
    if (spec.flipH) p.flipH = true;
    if (spec.flipV) p.flipV = true;
    if (spec.opacity !== undefined && spec.opacity < 1) p.opacity = rnd(Math.max(0, spec.opacity), 4);
    if (spec.blend) p.blend = spec.blend;
    if (spec.hidden) p.visible = false;
    const id = S().create(spec.type, parentId, p);
    state.n++;
    if (spec.kids) { const kx = spec.origin ? spec.origin[0] : spec.x, ky = spec.origin ? spec.origin[1] : spec.y; for (const k of spec.kids) buildSpec(k, id, kx, ky, state); }
    return id;
  }
  async function imageDims(blob) {
    try { if (typeof createImageBitmap === 'function') { const bm = await createImageBitmap(blob), out = {w: bm.width, h: bm.height, bitmap: bm}; return out; } } catch (e) { /* try the old way */ }
    return new Promise(res => { const url = URL.createObjectURL(blob), im = new Image(); im.onload = () => { res({w: im.naturalWidth, h: im.naturalHeight, img: im, url: url}); }; im.onerror = () => { URL.revokeObjectURL(url); res(null); }; im.src = url; });
  }
  function freeDims(d) { if (!d) return; if (d.bitmap && d.bitmap.close) d.bitmap.close(); if (d.url) URL.revokeObjectURL(d.url); }
  function viewCentre() { const sz = R().size || {w: 800, h: 600}; return R().screenToWorld(sz.w / 2, sz.h / 2); }
  /* where a new thing of this size goes: {parent, x, y} with its centre on the world point */
  function dropSpot(at, page, w, hh) {
    const c = at && isFinite(at.x) && isFinite(at.y) ? [at.x, at.y] : viewCentre();
    const cur = HD.sel.page, pg = page && node(page) && typeOf(page) === 'PAGE' ? page : cur;
    let parent = pg;
    if (pg === cur) { try { parent = U().containerAt(c[0], c[1]) || pg; } catch (e) { parent = pg; } }
    /* into the frame under the point only when the new thing fits in it (a big picture is not cut off by a small frame) */
    for (let g = 0; g < 100 && parent !== pg && node(parent); g++) { const pn = node(parent); if (Wn(pn) >= (w || 0) && Hn(pn) >= (hh || 0)) break; parent = pn.parent || pg; }
    if (!node(parent) || typeOf(parent) === 'DOCUMENT') parent = pg;
    const pt = typeOf(parent), loc = pt === 'PAGE' || !pt ? c : M.apply(M.inv(S().worldMatrix(parent)), c[0], c[1]);
    return {parent: parent, x: loc[0], y: loc[1]};
  }
  function leftNote(left, capped) {
    const notes = [];
    if (capped) notes.push('it has more than ' + commas(SVG_MAX_NODES) + ' shapes, so only the first ' + commas(SVG_MAX_NODES) + ' came in');
    if (left.unsafe) notes.push(left.unsafe + (left.unsafe === 1 ? ' script or embedded page was left out' : ' scripts or embedded pages were left out'));
    if (left.outside) notes.push(left.outside + (left.outside === 1 ? ' link to an outside file was left out' : ' links to outside files were left out'));
    if (left.clip + left.mask) notes.push((left.clip + left.mask) + (left.clip + left.mask === 1 ? ' mask could not be kept' : ' masks could not be kept'));
    if (left.text) notes.push('some stretched text is shown without its stretch');
    if (left.other) notes.push(left.other + (left.other === 1 ? ' part is not supported and was left out' : ' parts are not supported and were left out'));
    return notes.length ? ' Note: ' + notes.join('; ') + '.' : '';
  }
  /* SVG text -> real layers inside one new frame, centred on at {x, y} (world; the middle of the view when missing) */
  async function importSvg(text, at, opts) {
    opts = opts || {};
    if (!canEdit()) { toast('This file is view only.'); return null; }
    let res;
    try { res = svgRead(text, {name: opts.name}); } catch (e) { toast((e && e.message) || 'This SVG could not be read.', true); return null; }
    if (!res.spec.kids.length) { toast('There was nothing to import in this SVG.' + leftNote(res.left, res.capped), true); return null; }
    let lost = 0;
    for (const u of res.uploads) {                                   /* pictures first, so the import itself is one step */
      if (u.spec.late && u.spec.late.auto) {
        const d = await imageDims(u.blob), L = u.spec.late;
        if (d && d.w > 0 && d.h > 0) placeImageSpec(u.spec, L.w > 0 ? L.w : L.h > 0 ? L.h * d.w / d.h : d.w, L.h > 0 ? L.h : L.w > 0 ? L.w * d.h / d.w : d.h);
        freeDims(d);
      }
      let hash = null;
      try { hash = await UI().uploadImage(u.blob); } catch (e) { hash = null; }
      if (hash) u.fill.hash = hash; else { lost++; u.fill.type = 'solid'; u.fill.color = '#E3E3E8'; delete u.fill.hash; delete u.fill.mode; }
    }
    if (!canEdit() || !HD.app || !HD.app.file) return null;
    const spot = dropSpot(at || (isFinite(opts.x) ? {x: opts.x, y: opts.y} : null), opts.page, res.spec.w, res.spec.h), spec = res.spec, state = {n: 0, capped: res.capped};
    spec.x = Math.round(spot.x - spec.w / 2); spec.y = Math.round(spot.y - spec.h / 2); spec.origin = [0, 0];
    let id = null;
    S().tx('Import SVG', () => { id = buildSpec(spec, spot.parent, 0, 0, state); });
    if (!id) { toast('The SVG could not be added to this file.', true); return null; }
    HD.sel.set([id]);
    toast('Imported \u201C' + spec.name + '\u201D as ' + commas(state.n) + (state.n === 1 ? ' layer.' : ' layers.') + (lost ? ' ' + lost + ' picture' + (lost === 1 ? '' : 's') + ' could not be uploaded.' : '') + leftNote(res.left, state.capped), !!lost);
    return {id: id, nodes: state.n, capped: state.capped, left: res.left};
  }

  /* ================================================================ picture import */
  const IMG_SIDE = 4096, IMG_ROW_GAP = 24;
  async function headKind(blob) { try { return sniff(new Uint8Array(await blob.slice(0, 16).arrayBuffer())); } catch (e) { return ''; } }
  /* a picture file -> {blob, w, h}: checked by its first bytes, made smaller when a side is over 4096 px */
  async function prepImage(file) {
    const kind = await headKind(file);
    if (!kind) throw new Error('not a PNG, JPG, WebP or GIF picture');
    const d = await imageDims(file);
    if (!d || !(d.w > 0) || !(d.h > 0)) { freeDims(d); throw new Error('the picture could not be opened'); }
    let blob = file.type === kind ? file : file.slice(0, file.size, kind), w = d.w, hh = d.h;
    const k = Math.min(1, IMG_SIDE / Math.max(w, hh));
    if (k < 1 || blob.size > IMG_MAX) {
      const cw = Math.max(1, Math.round(w * k)), ch = Math.max(1, Math.round(hh * k)), cv = document.createElement('canvas');
      cv.width = cw; cv.height = ch;
      const ctx = cv.getContext('2d'); ctx.imageSmoothingQuality = 'high'; ctx.drawImage(d.bitmap || d.img, 0, 0, cw, ch);
      blob = await canvasBlob(cv, kind === 'image/jpeg' ? 'image/jpeg' : 'image/png', 0.9);
      if (blob.size > IMG_MAX) blob = await canvasBlob(cv, 'image/jpeg', 0.85);
      w = cw; hh = ch;
    }
    freeDims(d);
    if (blob.size > IMG_MAX) throw new Error('the picture is over 10 MB');
    return {blob: blob, w: w, h: hh};
  }
  function baseName(name, fallback) { const s = String(name || '').replace(/\.[a-z0-9]{1,8}$/i, '').replace(/\s+/g, ' ').trim().slice(0, 80); return s || fallback; }
  /* files -> rectangles with an image fill at the picture's own size, in one tidy row centred on `at`, as ONE step */
  async function importImages(files, at) {
    if (!canEdit()) { toast('This file is view only.'); return []; }
    const list = Array.from(files || []).slice(0, 24), made = [], bad = [];
    for (const f of list) {
      try { const p = await prepImage(f), hash = await UI().uploadImage(p.blob); if (!hash) { bad.push(f.name || 'picture'); continue; } made.push({hash: hash, w: p.w, h: p.h, name: baseName(f.name, 'Image')}); }
      catch (e) { bad.push((f.name || 'A picture') + ': ' + ((e && e.message) || 'could not be read')); }
    }
    if (!made.length) { toast(bad.length ? 'Not placed. ' + bad[0] + '.' : 'There was no picture to place.', true); return []; }
    if (!canEdit() || !HD.app || !HD.app.file) return [];
    const total = made.reduce((s, p) => s + p.w, 0) + IMG_ROW_GAP * (made.length - 1), spot = dropSpot(at, null, total, Math.max.apply(null, made.map(p => p.h))), ids = [];
    let x = spot.x - total / 2;
    S().tx(made.length === 1 ? 'Place image' : 'Place images', () => {
      for (const p of made) {
        ids.push(S().create('RECT', spot.parent, {name: p.name, x: Math.round(x), y: Math.round(spot.y - p.h / 2), w: p.w, h: p.h, fills: [{type: 'image', hash: p.hash, mode: 'fill', opacity: 1, visible: true}]}));
        x += p.w + IMG_ROW_GAP;
      }
    });
    HD.sel.set(ids);
    if (bad.length) toast(made.length + ' placed. Not placed: ' + bad[0] + (bad.length > 1 ? ' and ' + (bad.length - 1) + ' more' : '') + '.', true);
    return ids;
  }
  function isSvgFile(f) { return /svg/i.test(f.type || '') || /\.svg$/i.test(f.name || ''); }
  function isCopyFile(f) { return /\.hoola\.json$/i.test(f.name || ''); }
  function isRaster(f) { return /^image\/(png|jpeg|jpg|webp|gif)$/i.test(f.type || '') || /\.(png|jpe?g|webp|gif)$/i.test(f.name || ''); }
  /* files from a picker, a drop or a paste, put where they belong */
  async function placeFiles(files, at) {
    files = Array.from(files || []);
    const svgs = files.filter(isSvgFile), pics = files.filter(f => !isSvgFile(f) && isRaster(f));
    if (!svgs.length && !pics.length) { toast('Hoola Design can place PNG, JPG, WebP, GIF and SVG files.', true); return []; }
    const out = [];
    if (pics.length) for (const id of await importImages(pics, at)) out.push(id);
    let i = 0;
    for (const f of svgs.slice(0, 12)) {
      if (f.size > SVG_MAX_CHARS) { toast('\u201C' + f.name + '\u201D is over 20 MB, too big to import.', true); continue; }
      const c = at || (() => { const v = viewCentre(); return {x: v[0], y: v[1]}; })();
      const r = await importSvg(await blobText(f), {x: c.x + i * 40, y: c.y + i * 40}, {name: baseName(f.name, 'SVG')});
      if (r) { out.push(r.id); i++; }
    }
    if (out.length > 1) HD.sel.set(out.filter(id => node(id)));
    return out;
  }
  function pickFiles(accept, multiple) {
    return new Promise(res => {
      const inp = document.createElement('input');
      inp.type = 'file'; inp.accept = accept; inp.multiple = !!multiple; inp.className = 'hdx-file'; inp.setAttribute('aria-hidden', 'true'); inp.tabIndex = -1;
      inp.style.cssText = 'position:fixed;left:-9999px;top:0;width:1px;height:1px;opacity:0';
      let done = false;
      const finish = list => { if (done) return; done = true; if (inp.parentNode) inp.parentNode.removeChild(inp); res(list); };
      inp.addEventListener('change', () => finish(Array.from(inp.files || [])));
      inp.addEventListener('cancel', () => finish([]));
      document.body.appendChild(inp); inp.click();
      setTimeout(() => { if (!done && !inp.files.length && !document.body.contains(inp)) finish([]); }, 600000);
    });
  }
  async function pickAndPlace(kind) {
    if (!canEdit()) { toast('This file is view only.'); return []; }
    const files = await pickFiles(kind === 'svg' ? 'image/svg+xml,.svg' : 'image/png,image/jpeg,image/webp,image/gif,image/svg+xml,.png,.jpg,.jpeg,.webp,.gif,.svg', true);
    return files.length ? placeFiles(files, null) : [];
  }

  /* ================================================================ .hoola.json: the backup and move format */
  const COPY_FORMAT = 'hoola-design', COPY_EMBED_MAX = 48 * 1024 * 1024;
  function b64(bytes) { let s = ''; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000)); return btoa(s); }
  function unb64(str) { const bin = atob(String(str).replace(/\s+/g, '')), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }
  function assetHashes(nodes) {
    const seen = new Set();
    const look = v => { if (!v || typeof v !== 'object') return; if (Array.isArray(v)) { for (const x of v) look(x); return; } if (v.type === 'image' && typeof v.hash === 'string' && /^[A-Za-z0-9_.-]{4,160}$/.test(v.hash)) seen.add(v.hash); for (const k in v) if (typeof v[k] === 'object') look(v[k]); };
    for (const id in nodes) { const n = nodes[id]; if (!n) continue; look(n.fills); look(n.strokes); look(n.runs); if (n.styles) look(n.styles); if (n.ov) look(n.ov); }
    return Array.from(seen);
  }
  async function fetchAsset(hash) {
    const url = typeof R().assetURL === 'function' ? R().assetURL(hash) : '/api/design/assets/' + encodeURIComponent(hash), token = (UI() && UI().token) || '';
    const r = await fetch(url, token ? {headers: {Authorization: 'Bearer ' + token}} : undefined);
    if (!r.ok) throw new Error('asset ' + r.status);
    return r.blob();
  }
  /* the whole document as one JSON file: the nodes as the store has them, the pictures by hash and (while they fit) inside the file too */
  async function saveCopy() {
    const nodes = JSON.parse(JSON.stringify(S().toDoc().nodes)), hashes = assetHashes(nodes), assets = {};
    let total = 0, missing = 0;
    for (const hsh of hashes) {
      assets[hsh] = null;
      if (total > COPY_EMBED_MAX) { missing++; continue; }
      try { const blob = await fetchAsset(hsh), bytes = await blobBytes(blob); if (total + bytes.length > COPY_EMBED_MAX) { missing++; continue; } total += bytes.length; assets[hsh] = {type: sniff(bytes) || blob.type || 'image/png', data: b64(bytes)}; }
      catch (e) { missing++; }
    }
    const out = {format: COPY_FORMAT, version: 1, name: fileName(), saved_at: new Date().toISOString(), node_count: Object.keys(nodes).length, nodes: nodes, assets: assets};
    const name = safeName(fileName()) + '.hoola.json';
    download(new Blob([JSON.stringify(out)], {type: 'application/json'}), name);
    toast('Saved ' + name + ' (' + commas(out.node_count) + ' layers' + (hashes.length ? ', ' + (hashes.length - missing) + ' of ' + hashes.length + ' pictures inside' : '') + ').' + (missing ? ' The other pictures are kept by reference only.' : ''));
    return out;
  }
  const NO_REMAP = {chars: 1, name: 1, path: 1, desc: 1, url: 1, font: 1, bind: 1, fillStyle: 1, textStyle: 1, effectStyle: 1, styles: 1, vars: 1, modes: 1, hash: 1, color: 1, type: 1, idx: 1};
  function remapValue(v, key, map, hashMap) {
    if (typeof v === 'string') return key === 'hash' ? (hashMap[v] || v) : NO_REMAP[key] ? v : (map.has(v) ? map.get(v) : v);
    if (!v || typeof v !== 'object') return v;
    if (Array.isArray(v)) return v.map(x => remapValue(x, key, map, hashMap));
    if (NO_REMAP[key] && key !== 'styles') return v;
    const out = {};
    for (const k in v) {
      const nk = key === 'ov' ? k.split('/').map(p => (map.has(p) ? map.get(p) : p)).join('/') : k;
      out[nk] = remapValue(v[k], key === 'ov' || key === 'styles' ? '' : k, map, hashMap);
    }
    return out;
  }
  /* send a whole document into a (new, empty) file through its own room connection, in chunks, every id made fresh */
  function sendDocument(fileId, nodes, hashMap, onStep) {
    return new Promise((resolve, reject) => {
      const token = (UI() && UI().token) || '';
      let sock, done = false, timer = 0;
      const fail = msg => { if (done) return; done = true; clearTimeout(timer); try { sock.close(); } catch (e) { /* closed */ } reject(new Error(msg)); };
      try { sock = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/api/design/ws?file=' + encodeURIComponent(fileId), ['hoola', 'hoola-key.' + token]); }
      catch (e) { reject(new Error('The new file could not be reached.')); return; }
      const arm = () => { clearTimeout(timer); timer = setTimeout(() => fail('The server stopped answering while the copy was being written.'), 45000); };
      let chunks = [], sent = 0, rejected = 0, total = 0;
      arm();
      sock.onerror = () => fail('The connection to the new file broke.');
      sock.onclose = () => { if (!done) fail('The connection to the new file closed too early.'); };
      sock.onmessage = ev => {
        let m; try { m = JSON.parse(ev.data); } catch (e) { return; }
        if (m.t === 'init') {
          const cid = m.cid, have = (m.doc && m.doc.nodes) || {}, ROOT = '0:0';
          let page0 = null, n = 0;
          for (const id in have) if (have[id] && have[id].type === 'PAGE' && (page0 === null || String(have[id].idx) < String(have[page0].idx))) page0 = id;
          const kidsOf = new Map();
          for (const id in nodes) { const nd = nodes[id]; if (!nd || typeof nd !== 'object' || id === ROOT) continue; const list = kidsOf.get(nd.parent) || []; list.push(id); kidsOf.set(nd.parent, list); }
          const byIdx = (a, b) => (String(nodes[a].idx) < String(nodes[b].idx) ? -1 : String(nodes[a].idx) > String(nodes[b].idx) ? 1 : 0);
          const order = [], map = new Map([[ROOT, ROOT]]), queue = [ROOT];
          let firstPage = true;
          while (queue.length && order.length < 200000) {
            const pid = queue.shift(), kids = (kidsOf.get(pid) || []).sort(byIdx);
            for (const k of kids) { if (map.has(k)) continue; if (pid === ROOT && nodes[k].type === 'PAGE' && firstPage && page0) { map.set(k, page0); firstPage = false; } else map.set(k, cid + ':' + (++n)); order.push(k); queue.push(k); }
          }
          const ops = [], rootP = {};
          for (const k in (nodes[ROOT] || {})) if (k !== 'type' && k !== 'parent' && k !== 'idx' && k !== 'name') rootP[k] = remapValue(nodes[ROOT][k], k, map, hashMap);
          if (Object.keys(rootP).length) ops.push({id: ROOT, p: rootP});
          for (const old of order) {
            const src = nodes[old], id = map.get(old), p = {};
            for (const k in src) { if (k === 'parent') p.parent = map.get(src.parent); else p[k] = remapValue(src[k], k, map, hashMap); }
            if (id === page0) { delete p.type; delete p.parent; }
            ops.push({id: id, p: p});
          }
          total = ops.length;
          let cur = [], size = 0;
          for (const op of ops) { const sz = JSON.stringify(op).length; if (sz > 250000) { rejected++; continue; } if (cur.length >= 400 || size + sz > 220000) { chunks.push(cur); cur = []; size = 0; } cur.push(op); size += sz; }
          if (cur.length) chunks.push(cur);
          if (!chunks.length) { done = true; clearTimeout(timer); sock.close(); resolve({ops: 0, rejected: rejected}); return; }
          sock.send(JSON.stringify({t: 'ops', n: 1, ops: chunks[0]})); arm();
        } else if (m.t === 'ack') {
          rejected += Array.isArray(m.rejected) ? m.rejected.length : 0; sent++;
          if (onStep) onStep(sent, chunks.length);
          if (sent >= chunks.length) { done = true; clearTimeout(timer); try { sock.close(); } catch (e) { /* closed */ } resolve({ops: total, rejected: rejected}); return; }
          sock.send(JSON.stringify({t: 'ops', n: sent + 1, ops: chunks[sent]})); arm();
        }
      };
    });
  }
  async function importCopy(file) {
    if (!file) return null;
    if (file.size > 400 * 1024 * 1024) { toast('That file is over 400 MB, too big to import.', true); return null; }
    let data;
    try { data = JSON.parse(await blobText(file)); } catch (e) { toast('This file is not a Hoola Design copy (.hoola.json).', true); return null; }
    const nodes = data && (data.nodes || (data.doc && data.doc.nodes));
    if (!nodes || typeof nodes !== 'object' || !nodes['0:0'] || nodes['0:0'].type !== 'DOCUMENT') { toast('This file is not a Hoola Design copy (.hoola.json).', true); return null; }
    const count = Object.keys(nodes).length;
    if (count > 200000) { toast('That copy has more than 200,000 layers, more than a file can hold.', true); return null; }
    toast('Importing \u201C' + (data.name || baseName(file.name, 'Untitled')) + '\u201D\u2026');
    try {
      const f = await UI().api('POST', '/files', {name: String(data.name || baseName(String(file.name || '').replace(/\.hoola$/i, ''), 'Imported design')).slice(0, 120)});
      const hashMap = {}, assets = data.assets && typeof data.assets === 'object' ? data.assets : {};
      let lostPics = 0;
      for (const hsh in assets) {
        const a = assets[hsh];
        if (!a || typeof a.data !== 'string') continue;
        try { const bytes = unb64(a.data), kind = sniff(bytes); if (!kind || bytes.length > IMG_MAX) { lostPics++; continue; } const r = await UI().api('POST', '/files/' + encodeURIComponent(f.id) + '/assets', new Blob([bytes], {type: kind})); if (r && r.hash) hashMap[hsh] = r.hash; else lostPics++; }
        catch (e) { lostPics++; }
      }
      const res = await sendDocument(f.id, nodes, hashMap);
      toast('Imported ' + commas(res.ops - res.rejected) + ' layers into a new file.' + (res.rejected ? ' ' + res.rejected + ' could not be kept.' : '') + (lostPics ? ' ' + lostPics + ' pictures could not be uploaded.' : ''), res.rejected > 0);
      location.hash = '#/f/' + encodeURIComponent(f.id);
      return {id: f.id, ops: res.ops, rejected: res.rejected};
    } catch (e) { toast('The copy could not be imported: ' + ((e && e.message) || 'the server refused it') + '.', true); return null; }
  }
  async function pickCopy() { const files = await pickFiles('.json,.hoola.json,application/json', false); return files.length ? importCopy(files[0]) : null; }

  /* ================================================================ Inspect: the values of a layer, and code for it */
  function hexRgb(hex) {
    let x = String(hex || '').replace('#', '');
    if (x.length === 3 || x.length === 4) x = x.split('').map(c => c + c).join('');
    if (!/^[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(x)) return {r: 0, g: 0, b: 0, a: 1};
    return {r: parseInt(x.slice(0, 2), 16), g: parseInt(x.slice(2, 4), 16), b: parseInt(x.slice(4, 6), 16), a: x.length === 8 ? parseInt(x.slice(6), 16) / 255 : 1};
  }
  function col(color, opacity) { const c = hexRgb(color); c.a = clamp(c.a * (opacity === undefined || opacity === null ? 1 : +opacity), 0, 1); return c; }
  function hex2(v) { return ('0' + clamp(Math.round(v), 0, 255).toString(16)).slice(-2).toUpperCase(); }
  function hexOf(c) { return '#' + hex2(c.r) + hex2(c.g) + hex2(c.b); }
  function alphaText(a) { return String(rnd(a, a < 0.1 ? 3 : 2)); }
  function hslOf(c) {
    const r = c.r / 255, g = c.g / 255, b = c.b / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn;
    let hh = 0, s = 0;
    if (d) { s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn); hh = mx === r ? ((g - b) / d + (g < b ? 6 : 0)) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; hh *= 60; }
    return [Math.round(hh) % 360, Math.round(s * 100), Math.round(l * 100)];
  }
  /* a colour as text in the chosen way: 'hex' | 'rgb' | 'hsl' */
  function colorText(c, mode) {
    if (mode === 'rgb') return c.a < 1 ? 'rgba(' + c.r + ', ' + c.g + ', ' + c.b + ', ' + alphaText(c.a) + ')' : 'rgb(' + c.r + ', ' + c.g + ', ' + c.b + ')';
    if (mode === 'hsl') { const v = hslOf(c); return c.a < 1 ? 'hsla(' + v[0] + ', ' + v[1] + '%, ' + v[2] + '%, ' + alphaText(c.a) + ')' : 'hsl(' + v[0] + ', ' + v[1] + '%, ' + v[2] + '%)'; }
    return c.a < 1 ? hexOf(c) + hex2(c.a * 255) : hexOf(c);
  }
  function cssColor(c) { return c.a < 1 ? 'rgba(' + c.r + ', ' + c.g + ', ' + c.b + ', ' + alphaText(c.a) + ')' : hexOf(c); }
  function pxv(v) { const r = rnd(v, 2); return r === 0 ? '0' : r + 'px'; }
  const BOXY = {RECT: 1, ELLIPSE: 1, FRAME: 1, COMPONENT: 1, COMPONENT_SET: 1, INSTANCE: 1, SECTION: 1};
  const PATHY = {VECTOR: 1, POLYGON: 1, STAR: 1};
  const LAY0 = {mode: 'none', gap: 0, pad: [0, 0, 0, 0], alignMain: 'start', alignCross: 'start', wrap: false};

  /* the node as the code writers see it (an instance borrows what it does not set itself from its component) */
  function eff(id) {
    const n = node(id);
    if (n && n.type === 'INSTANCE' && n.comp && node(n.comp)) { const c = node(n.comp), out = Object.assign({}, c, n); out.type = 'INSTANCE'; out._kids = n.comp; return out; }
    return n;
  }
  function kidsOf(id) { const n = node(id); const src = n && n.type === 'INSTANCE' && n.comp && node(n.comp) ? n.comp : id; return S().children(src).filter(k => P(k, 'visible') !== false); }
  function layoutOf(n) { return n && LY().hasLayout(Object.assign({}, n, n.type === 'INSTANCE' ? {type: 'FRAME'} : null)) ? Object.assign({}, LAY0, G(n, 'layout')) : null; }
  function radiiOf(n, w, hh) {
    if (n.type === 'ELLIPSE') return null;
    const r = G(n, 'radius'), lim = Math.min(w, hh) / 2;
    const a = Array.isArray(r) ? [0, 1, 2, 3].map(i => clamp(num(+r[i], 0), 0, lim)) : [0, 0, 0, 0].map(() => clamp(num(+r, 0), 0, lim));
    return a.some(v => v > 0) ? a.map(v => rnd(v, 2)) : null;
  }
  function insideBorder(n) {
    if (!n || !BOXY[n.type]) return 0;
    const strokes = LY().paints(n, 'strokes').filter(vis), sw = num(+G(n, 'strokeWeight'), 1);
    return strokes.length && sw > 0 && (G(n, 'strokeAlign') || 'center') === 'inside' ? sw : 0;
  }
  function look(id) {
    const n = eff(id);
    if (!n) return null;
    const w = Wn(n), hh = Hn(n), pn = eff(n.parent), playout = pn ? layoutOf(pn) : null, lay = layoutOf(n);
    const m = {id: id, n: n, type: n.type, name: n.name || TYPE_LABEL[n.type] || 'Layer', x: num(n.x, 0), y: num(n.y, 0), w: w, h: hh, rot: num(n.rot, 0), flipH: !!n.flipH, flipV: !!n.flipV,
      opacity: clamp(num(+G(n, 'opacity'), 1), 0, 1), blend: G(n, 'blend') || 'normal', lay: lay, playout: playout, ptype: pn ? pn.type : '', pborder: insideBorder(pn),
      inFlow: !!playout && G(n, 'layoutPos') !== 'absolute', sizeH: G(n, 'sizeH') || 'fixed', sizeV: G(n, 'sizeV') || 'fixed',
      fills: LY().paints(n, 'fills').filter(vis), strokes: LY().paints(n, 'strokes').filter(vis), sw: num(+G(n, 'strokeWeight'), 1), align: G(n, 'strokeAlign') || 'center',
      dash: Array.isArray(G(n, 'dash')) && G(n, 'dash').length > 0, effects: LY().effects(n).filter(e => e && e.visible !== false), radii: radiiOf(n, w, hh),
      kids: kidsOf(id), clip: n.type !== 'GROUP' && n.type !== 'SECTION' && !!G(n, 'clip')};
    if (!(m.sw > 0)) m.strokes = [];
    if (n.type === 'TEXT') {
      const st = LY().baseStyle(n);
      m.text = {font: st.font, size: st.size, weight: st.weight, italic: st.italic, ls: st.ls, lh: st.lh, deco: st.deco, tcase: st.tcase, align: G(n, 'align') || 'left', alignV: G(n, 'alignV') || 'top', auto: G(n, 'autoResize') || 'wh',
        chars: String(G(n, 'chars') === undefined || G(n, 'chars') === null ? '' : G(n, 'chars'))};
    }
    return m;
  }
  /* ---- paints as CSS */
  function stopList(p, pos) {
    const stops = Array.isArray(p.stops) && p.stops.length ? p.stops : [{pos: 0, color: '#000000'}, {pos: 1, color: '#FFFFFF'}], po = p.opacity === undefined ? 1 : p.opacity;
    return stops.filter(Boolean).map(s => cssColor(col(s.color, (s.opacity === undefined ? 1 : s.opacity) * po)) + ' ' + pos(clamp(num(+s.pos, 0), 0, 1)));
  }
  function gradPts(p, w, hh) {
    const lin = p.type === 'linear', f = Array.isArray(p.from) ? p.from : (lin ? [0.5, 0] : [0.5, 0.5]), t = Array.isArray(p.to) ? p.to : (lin ? [0.5, 1] : [1, 0.5]);
    return {fx: num(+f[0], 0.5) * w, fy: num(+f[1], 0) * hh, tx: num(+t[0], 0.5) * w, ty: num(+t[1], 1) * hh, f: f, t: t};
  }
  /* a gradient paint as a CSS image, exact for a box of w x h (the canvas draws from / to in pixels; CSS wants an angle
     and stop places along ITS line through the middle, so both are worked out here) */
  function cssGradient(p, w, hh) {
    const g = gradPts(p, w, hh), dx = g.tx - g.fx, dy = g.ty - g.fy, L = Math.hypot(dx, dy);
    const pct = v => rnd(v * 100, 2) + '%';
    if (p.type === 'linear') {
      if (!(L > 0)) return null;
      const ux = dx / L, uy = dy / L, ang = Math.atan2(dx, -dy), cssLen = Math.abs(w * Math.sin(ang)) + Math.abs(hh * Math.cos(ang));
      if (!(cssLen > 0)) return null;
      const sx = w / 2 - ux * cssLen / 2, sy = hh / 2 - uy * cssLen / 2;
      const place = t => pct((((g.fx + dx * t) - sx) * ux + ((g.fy + dy * t) - sy) * uy) / cssLen);
      return 'linear-gradient(' + rnd(((ang / DEG) % 360 + 360) % 360, 2) + 'deg, ' + stopList(p, place).join(', ') + ')';
    }
    const at = pct(w ? g.fx / w : 0.5) + ' ' + pct(hh ? g.fy / hh : 0.5);
    if (p.type === 'radial') return 'radial-gradient(circle ' + pxv(Math.max(0.01, L)) + ' at ' + at + ', ' + stopList(p, pct).join(', ') + ')';
    if (p.type === 'angular') return 'conic-gradient(from ' + rnd((((Math.atan2(dy, dx) / DEG + 90) % 360) + 360) % 360, 2) + 'deg at ' + at + ', ' + stopList(p, v => rnd(v * 360, 2) + 'deg').join(', ') + ')';
    return null;
  }
  function assetName(m, ext) { return safeName(m.name) + '.' + ext; }
  /* the CSS `background` value of a fill stack, or null (CSS lists the TOP layer first) */
  function cssBackground(m) {
    const layers = [];
    for (let i = m.fills.length - 1; i >= 0; i--) {
      const p = m.fills[i], last = i === 0;
      if (p.type === 'image') layers.push('url("' + assetName(m, 'png') + '") ' + (p.mode === 'tile' ? 'repeat' : 'center / ' + (p.mode === 'fit' ? 'contain' : 'cover') + ' no-repeat'));
      else if (p.type === 'solid' || p.type === undefined) { const c = cssColor(col(p.color, p.opacity)); layers.push(last ? c : 'linear-gradient(' + c + ', ' + c + ')'); }
      else { const g = cssGradient(p, m.w, m.h); if (g) layers.push(g); }
    }
    return layers.length ? layers.join(', ') : null;
  }
  function firstColor(paints) {
    for (let i = paints.length - 1; i >= 0; i--) { const p = paints[i]; if (p.type === 'solid' || p.type === undefined) return col(p.color, p.opacity); if (Array.isArray(p.stops) && p.stops[0]) return col(p.stops[0].color, (p.stops[0].opacity === undefined ? 1 : p.stops[0].opacity) * (p.opacity === undefined ? 1 : p.opacity)); }
    return null;
  }
  function shadowCss(e, text) {
    const c = cssColor(col(e.color || '#000000', e.opacity === undefined ? 0.25 : e.opacity));
    return (e.type === 'inner' ? 'inset ' : '') + pxv(num(+e.x, 0)) + ' ' + pxv(num(+e.y, 0)) + ' ' + pxv(Math.max(0, num(+e.blur, 0))) + (text ? '' : ' ' + pxv(num(+e.spread, 0))) + ' ' + c;
  }
  function padCss(pad, b) { const p = [0, 1, 2, 3].map(i => Math.max(0, num(+pad[i], 0) - b)); return p; }
  function shortBox(p, f) { return p[0] === p[1] && p[1] === p[2] && p[2] === p[3] ? f(p[0]) : p[0] === p[2] && p[1] === p[3] ? f(p[0]) + ' ' + f(p[1]) : p[1] === p[3] ? f(p[0]) + ' ' + f(p[1]) + ' ' + f(p[2]) : p.map(f).join(' '); }
  const JUSTIFY = {start: 'flex-start', center: 'center', end: 'flex-end', between: 'space-between'}, ITEMS = {start: 'flex-start', center: 'center', end: 'flex-end', stretch: 'stretch'};
  const CASE_CSS = {upper: 'uppercase', lower: 'lowercase', title: 'capitalize'};
  function fontStack(f) { return '"' + String(f).replace(/["\\]/g, '') + '", sans-serif'; }

  /* CSS for one layer: [[property, value], ...] - right for what is on the canvas now */
  function cssPairs(id) {
    const m = look(id);
    if (!m) return [];
    const out = [], add = (k, v) => { if (v !== null && v !== undefined && v !== '') out.push([k, String(v)]); };
    const t = m.text, boxy = !!BOXY[m.type], horiz = m.playout && m.playout.mode === 'h';
    /* where it sits */
    if (m.inFlow) {
      const mainFill = (horiz ? m.sizeH : m.sizeV) === 'fill', crossFill = (horiz ? m.sizeV : m.sizeH) === 'fill';
      if (mainFill) add('flex', '1 1 0');
      if (crossFill) add('align-self', 'stretch');
    } else if (m.ptype && m.ptype !== 'PAGE' && m.ptype !== 'DOCUMENT') { add('position', 'absolute'); add('left', pxv(m.x - m.pborder)); add('top', pxv(m.y - m.pborder)); }
    if (!m.lay && m.kids.length && !t && !out.some(p => p[0] === 'position')) add('position', 'relative');          /* its children are placed from its corner */
    /* its size */
    const fillW = m.inFlow && m.sizeH === 'fill', fillH = m.inFlow && m.sizeV === 'fill', hugW = !!m.lay && m.sizeH === 'hug', hugH = !!m.lay && m.sizeV === 'hug';
    if (t) { if (t.auto !== 'wh' && !fillW) add('width', pxv(m.w)); if (t.auto === 'none' && !fillH) add('height', pxv(m.h)); }
    else if (m.type === 'LINE') { add('width', pxv(m.w)); add('height', '0'); }
    else {
      if (hugW) add('width', 'fit-content'); else if (!fillW) add('width', pxv(m.w));
      if (hugH) add('height', 'fit-content'); else if (!fillH) add('height', pxv(m.h));
    }
    for (const k of [['minW', 'min-width'], ['maxW', 'max-width'], ['minH', 'min-height'], ['maxH', 'max-height']]) if (num(m.n[k[0]], 0) > 0) add(k[1], pxv(m.n[k[0]]));
    /* auto layout */
    const border = boxy && m.strokes.length && m.sw > 0 && m.align === 'inside' ? m.sw : 0;
    if (m.lay) {
      add('display', 'flex'); add('flex-direction', m.lay.mode === 'h' ? 'row' : 'column');
      if (m.lay.wrap) add('flex-wrap', 'wrap');
      if (m.lay.alignMain !== 'start') add('justify-content', JUSTIFY[m.lay.alignMain] || 'flex-start');
      add('align-items', ITEMS[m.lay.alignCross] || 'flex-start');
      if (num(+m.lay.gap, 0) > 0) add('gap', pxv(m.lay.gap));
      const pad = padCss(Array.isArray(m.lay.pad) ? m.lay.pad : [0, 0, 0, 0], border);
      if (pad.some(v => v > 0)) add('padding', shortBox(pad, pxv));
    }
    if (boxy && (border || (m.lay && Array.isArray(m.lay.pad) && m.lay.pad.some(v => v > 0)))) add('box-sizing', 'border-box');
    /* paint */
    if (t) {
      const c = firstColor(m.fills), grad = m.fills.length && m.fills[m.fills.length - 1].type !== 'solid' && m.fills[m.fills.length - 1].type !== undefined && m.fills[m.fills.length - 1].type !== 'image' ? cssGradient(m.fills[m.fills.length - 1], m.w, m.h) : null;
      if (grad) { add('background', grad); add('-webkit-background-clip', 'text'); add('background-clip', 'text'); add('color', 'transparent'); } else if (c) add('color', cssColor(c));
      add('font-family', fontStack(t.font)); add('font-size', pxv(t.size)); add('font-weight', t.weight);
      if (t.italic) add('font-style', 'italic');
      add('line-height', t.lh === 'auto' ? '1.2' : pxv(t.lh));
      if (t.ls) add('letter-spacing', pxv(t.ls));
      if (t.align !== 'left') add('text-align', t.align);
      if (t.deco === 'underline') add('text-decoration', 'underline'); else if (t.deco === 'strike') add('text-decoration', 'line-through');
      if (CASE_CSS[t.tcase]) add('text-transform', CASE_CSS[t.tcase]);
      add('white-space', t.auto === 'wh' ? 'pre' : 'pre-wrap');
      if (m.strokes.length && m.sw > 0) { const sc = firstColor(m.strokes); if (sc) add('-webkit-text-stroke', pxv(m.sw) + ' ' + cssColor(sc)); }
    } else if (m.type === 'LINE') {
      const sc = firstColor(m.strokes); if (sc && m.sw > 0) add('border-top', pxv(m.sw) + ' ' + (m.dash ? 'dashed' : 'solid') + ' ' + cssColor(sc));
    } else if (PATHY[m.type]) {
      const fc = firstColor(m.fills), sc = firstColor(m.strokes);
      add('fill', fc ? cssColor(fc) : 'none'); if (sc && m.sw > 0) { add('stroke', cssColor(sc)); add('stroke-width', pxv(m.sw)); }
    } else if (boxy) {
      add('background', cssBackground(m));
      const sc = firstColor(m.strokes);
      if (sc && m.sw > 0) {
        const line = pxv(m.sw) + ' ' + (m.dash ? 'dashed' : 'solid') + ' ' + cssColor(sc);
        if (m.align === 'inside') add('border', line); else { add('outline', line); if (m.align === 'center') add('outline-offset', pxv(-m.sw / 2)); }
      }
      if (m.type === 'ELLIPSE') add('border-radius', '50%'); else if (m.radii) add('border-radius', shortBox(m.radii, pxv));
    }
    /* effects */
    const shadows = m.effects.filter(e => e.type === 'drop' || e.type === 'inner'), blur = m.effects.filter(e => e.type === 'blur'), bg = m.effects.filter(e => e.type === 'bgblur');
    if (shadows.length) {
      if (t) add('text-shadow', shadows.filter(e => e.type === 'drop').map(e => shadowCss(e, true)).join(', '));
      else if (boxy) add('box-shadow', shadows.map(e => shadowCss(e, false)).join(', '));
    }
    const filters = [];
    if (!t && !boxy) for (const e of shadows) if (e.type === 'drop') filters.push('drop-shadow(' + shadowCss(e, true) + ')');
    for (const e of blur) if (num(+e.blur, 0) > 0) filters.push('blur(' + pxv(e.blur / 2) + ')');
    if (filters.length) add('filter', filters.join(' '));
    if (bg.length && num(+bg[0].blur, 0) > 0) { add('-webkit-backdrop-filter', 'blur(' + pxv(bg[0].blur / 2) + ')'); add('backdrop-filter', 'blur(' + pxv(bg[0].blur / 2) + ')'); }
    if (m.opacity < 1) add('opacity', rnd(m.opacity, 3));
    const tf = [];
    if (m.rot) tf.push('rotate(' + rnd(m.rot, 2) + 'deg)');
    if (m.flipH) tf.push('scaleX(-1)');
    if (m.flipV) tf.push('scaleY(-1)');
    if (tf.length) add('transform', tf.join(' '));
    if (m.blend !== 'normal' && m.blend !== 'pass') add('mix-blend-mode', m.blend);
    if (m.clip && m.kids.length && boxy) add('overflow', 'hidden');
    return out;
  }
  function cssFor(id) {
    const m = look(id);
    if (!m) return '';
    let head = '/* ' + String(m.name).replace(/\*\//g, '* /') + ' */\n';
    if (PATHY[m.type]) head += '/* A vector shape: use the exported SVG. These are the values for its <path>. */\n';
    if (m.fills.some(p => p.type === 'image')) head += '/* The picture is an asset: export \u201C' + String(m.name).replace(/\*\//g, '') + '\u201D as PNG. */\n';
    if (m.strokes.some(p => p.type !== 'solid' && p.type !== undefined)) head += '/* The stroke is a gradient on the canvas; CSS shows its first colour. */\n';
    return head + cssPairs(id).map(p => p[0] + ': ' + p[1] + ';').join('\n');
  }

  /* ---- Flutter */
  function dn(v) { return String(rnd(v, 2)); }
  function dartStr(s) {
    let out = '';
    for (const ch of String(s)) { const c = ch.codePointAt(0);
      if (ch === '\\') out += '\\\\'; else if (ch === '\'') out += '\\\''; else if (ch === '$') out += '\\$'; else if (ch === '\n') out += '\\n'; else if (ch === '\r') out += '\\r'; else if (ch === '\t') out += '\\t';
      else if (c < 32 || c === 127) out += '\\u{' + c.toString(16) + '}'; else out += ch; }
    return '\'' + out + '\'';
  }
  function dartColor(c) { return 'Color(0x' + hex2(c.a * 255) + hex2(c.r) + hex2(c.g) + hex2(c.b) + ')'; }
  function applyCase(s, tc) { return tc === 'upper' ? s.toUpperCase() : tc === 'lower' ? s.toLowerCase() : tc === 'title' ? s.replace(/(^|\s)(\S)/g, (a, b, c) => b + c.toUpperCase()) : s; }
  function dartAlign(x, y) { return 'Alignment(' + dn(x * 2 - 1) + ', ' + dn(y * 2 - 1) + ')'; }
  function dartGradient(p, w, hh) {
    const stops = (Array.isArray(p.stops) && p.stops.length ? p.stops : [{pos: 0, color: '#000000'}, {pos: 1, color: '#FFFFFF'}]).filter(Boolean), po = p.opacity === undefined ? 1 : p.opacity, g = gradPts(p, w, hh);
    const colors = 'colors: [' + stops.map(s => dartColor(col(s.color, (s.opacity === undefined ? 1 : s.opacity) * po))).join(', ') + '], stops: [' + stops.map(s => dn(clamp(num(+s.pos, 0), 0, 1))).join(', ') + ']';
    const fxn = w ? g.fx / w : 0.5, fyn = hh ? g.fy / hh : 0.5, txn = w ? g.tx / w : 0.5, tyn = hh ? g.ty / hh : 0.5;
    if (p.type === 'linear') return 'LinearGradient(begin: ' + dartAlign(fxn, fyn) + ', end: ' + dartAlign(txn, tyn) + ', ' + colors + ')';
    if (p.type === 'radial') return 'RadialGradient(center: ' + dartAlign(fxn, fyn) + ', radius: ' + rnd(Math.hypot(g.tx - g.fx, g.ty - g.fy) / Math.max(0.01, Math.min(w, hh)), 4) + ', ' + colors + ')';
    if (p.type === 'angular') return 'SweepGradient(center: ' + dartAlign(fxn, fyn) + ', transform: GradientRotation(' + rnd(Math.atan2(g.ty - g.fy, g.tx - g.fx), 4) + '), ' + colors + ')';
    return null;
  }
  const FL_MAIN = {start: 'start', center: 'center', end: 'end', between: 'spaceBetween'};
  function flutterFor(id) {
    const budget = {n: 0};
    const lines = widget(id, 0, budget, null);
    return lines.join('\n') + '\n';
    function ind(lines2, by) { const pad = '  '.repeat(by); return lines2.map(l => pad + l); }
    function wrap(name, args, inner) { const out = [name + '(']; for (const a of args) { if (Array.isArray(a)) { a.forEach((l, i) => out.push('  ' + l + (i === a.length - 1 ? ',' : ''))); } else out.push('  ' + a + ','); } if (inner) { const c = inner.slice(); c[0] = 'child: ' + c[0]; c[c.length - 1] += ','; for (const l of c) out.push('  ' + l); } out.push(')'); return out; }
    function widget(nid, depth, bud, parentLay) {
      const m = look(nid);
      if (!m) return ['const SizedBox()'];
      bud.n++;
      const name = String(m.name).replace(/[\r\n]+/g, ' ').slice(0, 60);
      if (depth > 6 || bud.n > 60) return ['SizedBox(width: ' + dn(m.w) + ', height: ' + dn(m.h) + ') /* \u201C' + name.replace(/\*\//g, '') + '\u201D: export it, or select it to see its code */'];
      const horiz = parentLay && parentLay.mode === 'h';
      const mainFill = !!parentLay && m.inFlow && (horiz ? m.sizeH : m.sizeV) === 'fill', crossFill = !!parentLay && m.inFlow && (horiz ? m.sizeV : m.sizeH) === 'fill';
      const fillW = m.inFlow && m.sizeH === 'fill', fillH = m.inFlow && m.sizeV === 'fill';
      let core;
      if (m.text) {
        const t = m.text, st = [], c = firstColor(m.fills);
        if (c) st.push('color: ' + dartColor(c));
        st.push('fontFamily: ' + dartStr(t.font)); st.push('fontSize: ' + dn(t.size)); st.push('fontWeight: FontWeight.w' + clamp(Math.round(t.weight / 100) * 100, 100, 900));
        if (t.italic) st.push('fontStyle: FontStyle.italic');
        st.push('height: ' + (t.lh === 'auto' ? '1.2' : rnd(t.lh / t.size, 3)));
        if (t.ls) st.push('letterSpacing: ' + dn(t.ls));
        if (t.deco === 'underline') st.push('decoration: TextDecoration.underline'); else if (t.deco === 'strike') st.push('decoration: TextDecoration.lineThrough');
        const sh = m.effects.filter(e => e.type === 'drop');
        if (sh.length) st.push('shadows: [' + sh.map(e => 'Shadow(color: ' + dartColor(col(e.color || '#000000', e.opacity === undefined ? 0.25 : e.opacity)) + ', offset: Offset(' + dn(num(+e.x, 0)) + ', ' + dn(num(+e.y, 0)) + '), blurRadius: ' + dn(Math.max(0, num(+e.blur, 0))) + ')').join(', ') + ']');
        core = ['Text(', '  ' + dartStr(applyCase(t.chars, t.tcase)) + ','];
        if (t.align !== 'left') core.push('  textAlign: TextAlign.' + (t.align === 'justify' ? 'justify' : t.align) + ',');
        core.push('  style: TextStyle('); for (const s of st) core.push('    ' + s + ','); core.push('  ),'); core.push(')');
        if (t.auto !== 'wh' && !fillW) core = wrap('SizedBox', ['width: ' + dn(m.w)].concat(t.auto === 'none' && !fillH ? ['height: ' + dn(m.h)] : []), core);
      } else if (m.type === 'LINE') {
        const sc = firstColor(m.strokes);
        core = ['Container(width: ' + dn(m.w) + ', height: ' + dn(Math.max(0, m.sw)) + ', color: ' + (sc ? dartColor(sc) : 'const Color(0x00000000)') + ')'];
      } else if (PATHY[m.type]) {
        core = ['SvgPicture.asset(' + dartStr('assets/' + assetName(m, 'svg')) + ', width: ' + dn(m.w) + ', height: ' + dn(m.h) + ') /* a vector shape: export it as SVG (package flutter_svg) */'];
      } else {
        const args = [], deco = [];
        const hugW = !!m.lay && m.sizeH === 'hug', hugH = !!m.lay && m.sizeV === 'hug';
        if (!hugW && !(mainFill && horiz)) args.push('width: ' + (fillW && !horiz && crossFill ? 'double.infinity' : dn(m.w)));
        if (!hugH && !(mainFill && !horiz)) args.push('height: ' + (fillH && horiz && crossFill ? 'double.infinity' : dn(m.h)));
        const inset = m.type !== 'GROUP' && m.strokes.length && m.sw > 0 ? (m.align === 'inside' ? m.sw : m.align === 'outside' ? 0 : m.sw / 2) : 0;   /* Flutter insets a Container's child by its border */
        if (m.lay) { const p = padCss(Array.isArray(m.lay.pad) ? m.lay.pad : [0, 0, 0, 0], inset); if (p.some(v => v > 0)) args.push('padding: ' + (p[0] === p[1] && p[1] === p[2] && p[2] === p[3] ? 'EdgeInsets.all(' + dn(p[0]) + ')' : p[0] === p[2] && p[1] === p[3] ? 'EdgeInsets.symmetric(horizontal: ' + dn(p[1]) + ', vertical: ' + dn(p[0]) + ')' : 'EdgeInsets.fromLTRB(' + dn(p[3]) + ', ' + dn(p[0]) + ', ' + dn(p[1]) + ', ' + dn(p[2]) + ')')); }
        if (m.type !== 'GROUP') {
          const solids = m.fills.filter(p => p.type === 'solid' || p.type === undefined), grads = m.fills.filter(p => p.type === 'linear' || p.type === 'radial' || p.type === 'angular'), imgs = m.fills.filter(p => p.type === 'image');
          if (solids.length) deco.push('color: ' + dartColor(col(solids[0].color, solids[0].opacity)));
          if (grads.length) { const g = dartGradient(grads[grads.length - 1], m.w, m.h); if (g) deco.push('gradient: ' + g); }
          if (imgs.length) { const p = imgs[imgs.length - 1]; deco.push('image: DecorationImage(image: AssetImage(' + dartStr('assets/' + assetName(m, 'png')) + '), ' + (p.mode === 'tile' ? 'repeat: ImageRepeat.repeat' : 'fit: BoxFit.' + (p.mode === 'fit' ? 'contain' : 'cover')) + ')'); }
          const sc = firstColor(m.strokes);
          if (sc && m.sw > 0) deco.push('border: Border.all(color: ' + dartColor(sc) + ', width: ' + dn(m.sw) + ', strokeAlign: BorderSide.strokeAlign' + (m.align === 'inside' ? 'Inside' : m.align === 'outside' ? 'Outside' : 'Center') + ')');
          if (m.type === 'ELLIPSE') { if (Math.abs(m.w - m.h) < 0.01) deco.push('shape: BoxShape.circle'); else deco.push('borderRadius: BorderRadius.all(Radius.elliptical(' + dn(m.w / 2) + ', ' + dn(m.h / 2) + '))'); }
          else if (m.radii) { const r = m.radii; deco.push('borderRadius: ' + (r[0] === r[1] && r[1] === r[2] && r[2] === r[3] ? 'BorderRadius.circular(' + dn(r[0]) + ')' : 'BorderRadius.only(topLeft: Radius.circular(' + dn(r[0]) + '), topRight: Radius.circular(' + dn(r[1]) + '), bottomRight: Radius.circular(' + dn(r[2]) + '), bottomLeft: Radius.circular(' + dn(r[3]) + '))')); }
          const drops = m.effects.filter(e => e.type === 'drop');
          if (drops.length) deco.push('boxShadow: [' + drops.map(e => 'BoxShadow(color: ' + dartColor(col(e.color || '#000000', e.opacity === undefined ? 0.25 : e.opacity)) + ', offset: Offset(' + dn(num(+e.x, 0)) + ', ' + dn(num(+e.y, 0)) + '), blurRadius: ' + dn(Math.max(0, num(+e.blur, 0))) + ', spreadRadius: ' + dn(num(+e.spread, 0)) + ')').join(', ') + ']');
        }
        if (deco.length && m.clip && m.kids.length) args.push('clipBehavior: Clip.antiAlias');
        if (deco.length) args.push(['decoration: BoxDecoration('].concat(deco.map(d => '  ' + d + ','), [')']));
        let child = null;
        if (m.kids.length) {
          if (m.lay) {
            const horizIn = m.lay.mode === 'h', gap = num(+m.lay.gap, 0), flow = m.kids.filter(k => P(k, 'layoutPos') !== 'absolute'), items = [];
            flow.forEach((k, i) => {
              let wdg = widget(k, depth + 1, bud, m.lay);
              const km = look(k);
              if (km && (horizIn ? km.sizeH : km.sizeV) === 'fill') wdg = wrap('Expanded', [], wdg);
              if (i && gap > 0 && m.lay.alignMain !== 'between' && !m.lay.wrap) items.push(['SizedBox(' + (horizIn ? 'width' : 'height') + ': ' + dn(gap) + ')']);
              items.push(wdg);
            });
            if (m.lay.wrap) child = ['Wrap(', '  direction: Axis.' + (horizIn ? 'horizontal' : 'vertical') + ',', '  spacing: ' + dn(gap) + ',', '  runSpacing: ' + dn(gap) + ',', '  children: ['];
            else {
              child = [(horizIn ? 'Row' : 'Column') + '('];
              if ((horizIn ? m.sizeH : m.sizeV) === 'hug') child.push('  mainAxisSize: MainAxisSize.min,');
              if (m.lay.alignMain !== 'start') child.push('  mainAxisAlignment: MainAxisAlignment.' + (FL_MAIN[m.lay.alignMain] || 'start') + ',');
              if (m.lay.alignCross !== 'center') child.push('  crossAxisAlignment: CrossAxisAlignment.' + (m.lay.alignCross === 'end' ? 'end' : m.lay.alignCross === 'stretch' ? 'stretch' : 'start') + ',');
              child.push('  children: [');
            }
            for (const it of items) { const c = ind(it, 2); c[c.length - 1] += ','; for (const l of c) child.push(l); }
            child.push('  ],'); child.push(')');
          } else {
            child = ['Stack('];
            if (!m.clip) child.push('  clipBehavior: Clip.none,');
            child.push('  children: [');
            for (const k of m.kids) { const km = look(k); if (!km) continue; const pos = wrap('Positioned', ['left: ' + dn(km.x - inset), 'top: ' + dn(km.y - inset)], widget(k, depth + 1, bud, null)), c = ind(pos, 2); c[c.length - 1] += ','; for (const l of c) child.push(l); }
            child.push('  ],'); child.push(')');
          }
        }
        core = !args.length && child ? child : wrap(deco.length || m.lay || !child ? 'Container' : 'SizedBox', args, child);
        if (m.effects.some(e => e.type === 'inner')) core[core.length - 1] += ' /* the inner shadow needs a custom painter in Flutter */';
      }
      if (m.rot) core = wrap('Transform.rotate', ['angle: ' + rnd(m.rot * DEG, 4)], core);
      if (m.flipH || m.flipV) core = wrap('Transform.flip', (m.flipH ? ['flipX: true'] : []).concat(m.flipV ? ['flipY: true'] : []), core);
      if (m.opacity < 1) core = wrap('Opacity', ['opacity: ' + rnd(m.opacity, 3)], core);
      return core;
    }
  }

  /* ---- Tailwind (v3 names; an arbitrary value wherever the scale has no exact step) */
  const TW_SPACE = {0: '0', 1: 'px', 2: '0.5', 4: '1', 6: '1.5', 8: '2', 10: '2.5', 12: '3', 14: '3.5', 16: '4', 20: '5', 24: '6', 28: '7', 32: '8', 36: '9', 40: '10', 44: '11', 48: '12', 56: '14', 64: '16', 80: '20', 96: '24',
    112: '28', 128: '32', 144: '36', 160: '40', 176: '44', 192: '48', 208: '52', 224: '56', 240: '60', 256: '64', 288: '72', 320: '80', 384: '96'};
  const TW_RADIUS = {2: 'rounded-sm', 4: 'rounded', 6: 'rounded-md', 8: 'rounded-lg', 12: 'rounded-xl', 16: 'rounded-2xl', 24: 'rounded-3xl'};
  const TW_WEIGHT = {100: 'font-thin', 200: 'font-extralight', 300: 'font-light', 400: 'font-normal', 500: 'font-medium', 600: 'font-semibold', 700: 'font-bold', 800: 'font-extrabold', 900: 'font-black'};
  const TW_BORDER = {1: '', 2: '-2', 4: '-4', 8: '-8'};
  function twArb(v) { return String(v).replace(/,\s+/g, ',').replace(/\s+/g, '_'); }
  function twSp(prefix, v) { v = rnd(v, 2); if (v < 0) return prefix + '-[' + v + 'px]'; return TW_SPACE[v] !== undefined ? prefix + '-' + TW_SPACE[v] : prefix + '-[' + v + 'px]'; }
  function twColor(prefix, c) { if (c.a >= 1) { const hx = hexOf(c); return hx === '#FFFFFF' ? prefix + '-white' : hx === '#000000' ? prefix + '-black' : prefix + '-[' + hx + ']'; } return prefix + '-[' + twArb(cssColor(c)) + ']'; }
  function tailwindClasses(id) {
    const m = look(id);
    if (!m) return [];
    const out = [], t = m.text, boxy = !!BOXY[m.type], horiz = m.playout && m.playout.mode === 'h';
    if (m.inFlow) { if ((horiz ? m.sizeH : m.sizeV) === 'fill') out.push('flex-1'); if ((horiz ? m.sizeV : m.sizeH) === 'fill') out.push('self-stretch'); }
    else if (m.ptype && m.ptype !== 'PAGE' && m.ptype !== 'DOCUMENT') { out.push('absolute', twSp('left', m.x - m.pborder), twSp('top', m.y - m.pborder)); }
    if (!m.lay && m.kids.length && !t && out.indexOf('absolute') < 0) out.push('relative');
    const fillW = m.inFlow && m.sizeH === 'fill', fillH = m.inFlow && m.sizeV === 'fill', hugW = !!m.lay && m.sizeH === 'hug', hugH = !!m.lay && m.sizeV === 'hug';
    if (t) { if (t.auto !== 'wh' && !fillW) out.push(twSp('w', m.w)); if (t.auto === 'none' && !fillH) out.push(twSp('h', m.h)); }
    else if (m.type === 'LINE') out.push(twSp('w', m.w), 'h-0');
    else { if (hugW) out.push('w-fit'); else if (!fillW) out.push(twSp('w', m.w)); if (hugH) out.push('h-fit'); else if (!fillH) out.push(twSp('h', m.h)); }
    const border = boxy && m.strokes.length && m.sw > 0 && m.align === 'inside' ? m.sw : 0;
    if (m.lay) {
      out.push('flex'); if (m.lay.mode !== 'h') out.push('flex-col'); if (m.lay.wrap) out.push('flex-wrap');
      if (m.lay.alignMain !== 'start') out.push('justify-' + (m.lay.alignMain === 'between' ? 'between' : m.lay.alignMain));
      out.push('items-' + (m.lay.alignCross || 'start'));
      if (num(+m.lay.gap, 0) > 0) out.push(twSp('gap', m.lay.gap));
      const p = padCss(Array.isArray(m.lay.pad) ? m.lay.pad : [0, 0, 0, 0], border);
      if (p.some(v => v > 0)) { if (p[0] === p[1] && p[1] === p[2] && p[2] === p[3]) out.push(twSp('p', p[0])); else if (p[0] === p[2] && p[1] === p[3]) { if (p[1]) out.push(twSp('px', p[1])); if (p[0]) out.push(twSp('py', p[0])); } else { if (p[0]) out.push(twSp('pt', p[0])); if (p[1]) out.push(twSp('pr', p[1])); if (p[2]) out.push(twSp('pb', p[2])); if (p[3]) out.push(twSp('pl', p[3])); } }
    }
    if (t) {
      const c = firstColor(m.fills);
      if (c) out.push(twColor('text', c));
      out.push('font-[\'' + String(t.font).replace(/['\\\]]/g, '').replace(/\s+/g, '_') + '\']', 'text-[' + rnd(t.size, 2) + 'px]', TW_WEIGHT[clamp(Math.round(t.weight / 100) * 100, 100, 900)]);
      if (t.italic) out.push('italic');
      out.push(t.lh === 'auto' ? 'leading-[1.2]' : 'leading-[' + rnd(t.lh, 2) + 'px]');
      if (t.ls) out.push('tracking-[' + rnd(t.ls, 2) + 'px]');
      if (t.align !== 'left') out.push('text-' + t.align);
      if (t.deco === 'underline') out.push('underline'); else if (t.deco === 'strike') out.push('line-through');
      if (CASE_CSS[t.tcase]) out.push(CASE_CSS[t.tcase]);
      out.push(t.auto === 'wh' ? 'whitespace-pre' : 'whitespace-pre-wrap');
    } else if (m.type === 'LINE') {
      const sc = firstColor(m.strokes); if (sc && m.sw > 0) { out.push(TW_BORDER[m.sw] !== undefined ? 'border-t' + TW_BORDER[m.sw] : 'border-t-[' + rnd(m.sw, 2) + 'px]', twColor('border', sc)); if (m.dash) out.push('border-dashed'); }
    } else if (PATHY[m.type]) {
      const fc = firstColor(m.fills), sc = firstColor(m.strokes);
      out.push(fc ? twColor('fill', fc) : 'fill-none'); if (sc && m.sw > 0) out.push(twColor('stroke', sc), 'stroke-[' + rnd(m.sw, 2) + 'px]');
    } else if (boxy) {
      if (m.fills.length === 1 && (m.fills[0].type === 'solid' || m.fills[0].type === undefined)) out.push(twColor('bg', col(m.fills[0].color, m.fills[0].opacity)));
      else if (m.fills.length === 1 && m.fills[0].type === 'image') out.push('bg-[url(\'' + assetName(m, 'png').replace(/['\\\]\s]/g, '_') + '\')]', m.fills[0].mode === 'tile' ? 'bg-repeat' : m.fills[0].mode === 'fit' ? 'bg-contain' : 'bg-cover', 'bg-center', m.fills[0].mode === 'tile' ? '' : 'bg-no-repeat');
      else { const bgv = cssBackground(m); if (bgv) out.push('bg-[' + twArb(bgv.replace(/"/g, '\'')) + ']'); }
      const sc = firstColor(m.strokes);
      if (sc && m.sw > 0) {
        if (m.align === 'inside') { out.push(TW_BORDER[m.sw] !== undefined ? 'border' + TW_BORDER[m.sw] : 'border-[' + rnd(m.sw, 2) + 'px]', twColor('border', sc)); if (m.dash) out.push('border-dashed'); }
        else { out.push('outline', 'outline-[' + rnd(m.sw, 2) + 'px]', twColor('outline', sc)); if (m.dash) out.push('outline-dashed'); if (m.align === 'center') out.push('outline-offset-[' + rnd(-m.sw / 2, 2) + 'px]'); }
      }
      if (m.type === 'ELLIPSE') out.push('rounded-full');
      else if (m.radii) { const r = m.radii; if (r[0] === r[1] && r[1] === r[2] && r[2] === r[3]) out.push(TW_RADIUS[r[0]] || 'rounded-[' + r[0] + 'px]'); else ['tl', 'tr', 'br', 'bl'].forEach((k, i) => { if (r[i]) out.push('rounded-' + k + '-[' + r[i] + 'px]'); }); }
    }
    const shadows = m.effects.filter(e => e.type === 'drop' || e.type === 'inner'), blur = m.effects.filter(e => e.type === 'blur' && num(+e.blur, 0) > 0), bg = m.effects.filter(e => e.type === 'bgblur' && num(+e.blur, 0) > 0);
    if (shadows.length && boxy) out.push('shadow-[' + twArb(shadows.map(e => shadowCss(e, false)).join(',')) + ']');
    if (shadows.length && !boxy && !t) for (const e of shadows) if (e.type === 'drop') out.push('drop-shadow-[' + twArb(shadowCss(e, true)) + ']');
    if (blur.length) out.push('blur-[' + rnd(blur[0].blur / 2, 2) + 'px]');
    if (bg.length) out.push('backdrop-blur-[' + rnd(bg[0].blur / 2, 2) + 'px]');
    if (m.opacity < 1) { const o = rnd(m.opacity * 100, 2); out.push(o % 5 === 0 ? 'opacity-' + o : 'opacity-[' + rnd(m.opacity, 3) + ']'); }
    if (m.rot) out.push('rotate-[' + rnd(m.rot, 2) + 'deg]');
    if (m.flipH) out.push('-scale-x-100');
    if (m.flipV) out.push('-scale-y-100');
    if (m.blend !== 'normal' && m.blend !== 'pass') out.push('mix-blend-' + m.blend);
    if (m.clip && m.kids.length && boxy) out.push('overflow-hidden');
    return out.filter(Boolean);
  }
  function htmlEsc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function tailwindFor(id) {
    const bud = {n: 0};
    return el(id, 0).join('\n') + '\n';
    function el(nid, depth) {
      const m = look(nid);
      if (!m) return [];
      bud.n++;
      const pad = '  '.repeat(depth), cls = tailwindClasses(nid).join(' ');
      if (m.text) return [pad + '<p class="' + cls + '">' + htmlEsc(m.text.chars).replace(/\n/g, '&#10;') + '</p>'];
      if (!m.kids.length || PATHY[m.type] || m.type === 'LINE') return [pad + '<div class="' + cls + '"></div>'];
      if (depth > 6 || bud.n > 60) return [pad + '<div class="' + cls + '"><!-- more layers inside --></div>'];
      const out = [pad + '<div class="' + cls + '">'];
      for (const k of m.kids) for (const l of el(k, depth + 1)) out.push(l);
      out.push(pad + '</div>');
      return out;
    }
  }
  const CODE = {css: cssFor, flutter: flutterFor, tailwind: tailwindFor};
  const CODE_LABEL = {css: 'CSS', flutter: 'Flutter', tailwind: 'Tailwind'};
  function copyCode(lang, ids) {
    ids = selTop(ids);
    if (!ids.length) { toast('Select a layer to copy its code.'); return false; }
    const fn = CODE[lang] || cssFor;
    return copyText(ids.map(id => fn(id).replace(/\n+$/, '')).join('\n\n') + '\n', 'Copied as ' + (CODE_LABEL[lang] || 'CSS') + '.');
  }

  /* ================================================================ the Inspect tab */
  const insp = {ver: 0, lang: lsGet('hd.inspect.code', 'css'), color: lsGet('hd.inspect.color', 'hex')};
  if (!CODE[insp.lang]) insp.lang = 'css';
  if (!{hex: 1, rgb: 1, hsl: 1}[insp.color]) insp.color = 'hex';
  function segOwn(opts, cur, set, label) {
    const el = h('div', {class: 'hd-seg', role: 'radiogroup', 'aria-label': label});
    for (const o of opts) el.appendChild(h('button', {type: 'button', class: 'hd-segb' + (o[0] === cur ? ' on' : ''), role: 'radio', 'aria-checked': String(o[0] === cur), text: o[1], on: {click: () => set(o[0])}}));
    return el;
  }
  function kv(label, value, copyValue) {
    const v = String(value);
    return h('button', {class: 'hdx-kv', type: 'button', title: 'Copy ' + v, on: {click: () => copyText(copyValue === undefined ? v : String(copyValue), 'Copied ' + v + '.')}}, h('span', {class: 'hdx-k', text: label}), h('span', {class: 'hdx-v', text: v}));
  }
  /* the colours a selection uses, in the order met: [{c, hex, where}] */
  function coloursOf(ids) {
    const out = [], seen = new Set();
    let walked = 0;
    const push = (c, where) => { if (!c) return; const key = hexOf(c) + '/' + rnd(c.a, 3); if (seen.has(key) || out.length >= 24) return; seen.add(key); out.push({c: c, where: where}); };
    const paint = (p, where) => { if (!vis(p) || p.type === 'image') return; const po = p.opacity === undefined ? 1 : p.opacity;
      if (p.type === 'solid' || p.type === undefined) push(col(p.color, po), where); else if (Array.isArray(p.stops)) for (const s of p.stops) if (s) push(col(s.color, (s.opacity === undefined ? 1 : s.opacity) * po), where + ' gradient'); };
    const one = id => {
      const n = eff(id);
      if (!n || walked++ > 400 || G(n, 'visible') === false) return;
      for (const p of LY().paints(n, 'fills')) paint(p, n.type === 'TEXT' ? 'Text' : 'Fill');
      if (num(+G(n, 'strokeWeight'), 1) > 0) for (const p of LY().paints(n, 'strokes')) paint(p, 'Stroke');
      for (const e of LY().effects(n)) if (e && e.visible !== false && (e.type === 'drop' || e.type === 'inner')) push(col(e.color || '#000000', e.opacity === undefined ? 0.25 : e.opacity), 'Shadow');
      if (Array.isArray(n.runs)) for (const r of n.runs) if (r && Array.isArray(r.fills)) for (const p of r.fills) paint(p, 'Text');
      for (const k of kidsOf(id)) one(k);
    };
    for (const id of ids) one(id);
    return out;
  }
  /* layers in the selection that are meant to be exported: own export rows, or a picture fill */
  function assetsOf(ids) {
    const out = [];
    let walked = 0;
    const one = id => { const n = node(id); if (!n || walked++ > 2000 || out.length >= 60) return; const rows = rowsOf(id), pic = LY().paints(n, 'fills').some(p => vis(p) && p.type === 'image');
      if (rows.length || pic) out.push({id: id, name: n.name || TYPE_LABEL[n.type] || 'Layer', rows: rows, pic: pic}); for (const k of S().children(id)) one(k); };
    for (const id of ids) one(id);
    return out;
  }
  function parentGaps(id) {
    const n = node(id), par = n && n.parent, pn = node(par);
    if (!pn || pn.type === 'PAGE' || pn.type === 'DOCUMENT') return null;
    const b = R().exportBounds(id, 'box'), pw = Wn(pn), ph = Hn(pn);
    if (!b) return null;
    return {top: rnd(b.y, 2), right: rnd(pw - b.x - b.w, 2), bottom: rnd(ph - b.y - b.h, 2), left: rnd(b.x, 2), parent: pn.name || TYPE_LABEL[pn.type] || 'parent'};
  }
  function inspectRender(el) {
    const ids = (HD.sel.ids || []).filter(id => node(id)), sig = [ids.join(','), insp.ver, insp.lang, insp.color, HD.sel.page, canEdit()].join('|');
    if (el.dataset.hdxSig === sig && el.firstChild) return;
    el.dataset.hdxSig = sig; clear(el); el.classList.add('hdx-inspect');
    const again = () => { el.dataset.hdxSig = ''; UI().refresh(); }, section = (title, acts) => UI().section(el, title, acts || []);
    if (!ids.length) {
      const pg = node(HD.sel.page) || {}, frames = S().children(HD.sel.page).filter(id => CONT[typeOf(id)]);
      el.appendChild(h('div', {class: 'hd-selhead'}, h('span', {class: 'hd-ltype'}, UI().icon('page', 14)), h('span', {class: 'hd-selname', text: pg.name || 'Page'}), h('span', {class: 'hd-seltype', text: 'Page'})));
      const s = section('Page');
      s.body.appendChild(h('div', {class: 'hdx-kvs'}, kv('Background', colorText(col(P(HD.sel.page, 'bg') || '#F5F5F5', 1), insp.color)), kv('Frames', String(frames.length))));
      s.body.appendChild(h('p', {class: 'hd-note', text: 'Select a layer to see its size, colours, spacing and code.'}));
      if (frames.length) s.body.appendChild(h('button', {class: 'hd-btn hdx-wide', type: 'button', text: 'Export all frames\u2026', on: {click: () => exportDialog([])}}));
      return;
    }
    const id = ids[0], m = look(id), n0 = node(id);
    el.appendChild(h('div', {class: 'hd-selhead'}, h('span', {class: 'hd-ltype'}, UI().icon(ids.length === 1 ? ({FRAME: 'frame', GROUP: 'group', SECTION: 'section', RECT: 'rect', ELLIPSE: 'ellipse', LINE: 'line', POLYGON: 'polygon', STAR: 'star', VECTOR: 'vector', TEXT: 'text', COMPONENT: 'component', COMPONENT_SET: 'component', INSTANCE: 'instance'}[n0.type] || 'rect') : 'group', 14)),
      h('span', {class: 'hd-selname', text: ids.length === 1 ? m.name : ids.length + ' layers'}), h('span', {class: 'hd-seltype', text: ids.length === 1 ? (TYPE_LABEL[n0.type] || n0.type) : 'Selection'})));
    if (ids.length === 1) {
      const s = section('Layout'), grid = h('div', {class: 'hdx-kvs two'});
      grid.appendChild(kv('X', fx(m.x, 2))); grid.appendChild(kv('Y', fx(m.y, 2))); grid.appendChild(kv('W', fx(m.w, 2))); grid.appendChild(kv('H', fx(m.h, 2)));
      if (m.rot) grid.appendChild(kv('Rotation', fx(m.rot, 2) + '\u00B0'));
      if (m.opacity < 1) grid.appendChild(kv('Opacity', fx(m.opacity * 100, 1) + '%'));
      if (m.radii) grid.appendChild(kv('Radius', m.radii[0] === m.radii[1] && m.radii[1] === m.radii[2] && m.radii[2] === m.radii[3] ? fx(m.radii[0], 2) : m.radii.map(v => fx(v, 2)).join(' ')));
      if (m.strokes.length && m.sw > 0) grid.appendChild(kv('Stroke', fx(m.sw, 2) + ' ' + m.align));
      s.body.appendChild(grid);
      if (m.lay) { const g2 = h('div', {class: 'hdx-kvs two'}); g2.appendChild(kv('Direction', m.lay.mode === 'h' ? 'Row' : 'Column')); g2.appendChild(kv('Gap', fx(num(+m.lay.gap, 0), 2)));
        g2.appendChild(kv('Padding', shortBox((Array.isArray(m.lay.pad) ? m.lay.pad : [0, 0, 0, 0]).map(v => rnd(num(+v, 0), 2)), String))); g2.appendChild(kv('Align', m.lay.alignMain + ' / ' + m.lay.alignCross));
        s.body.appendChild(h('h4', {class: 'hdx-h4', text: 'Auto layout'})); s.body.appendChild(g2); }
      const gaps = parentGaps(id);
      if (gaps) { const g3 = h('div', {class: 'hdx-kvs two'}); g3.appendChild(kv('Top', fx(gaps.top, 2))); g3.appendChild(kv('Right', fx(gaps.right, 2))); g3.appendChild(kv('Bottom', fx(gaps.bottom, 2))); g3.appendChild(kv('Left', fx(gaps.left, 2)));
        s.body.appendChild(h('h4', {class: 'hdx-h4', text: 'Space to \u201C' + gaps.parent + '\u201D'})); s.body.appendChild(g3); }
      if (m.text) {
        const t = m.text, st = section('Text'), g4 = h('div', {class: 'hdx-kvs two'});
        g4.appendChild(kv('Font', t.font)); g4.appendChild(kv('Weight', String(t.weight) + (t.italic ? ' italic' : ''), t.weight)); g4.appendChild(kv('Size', fx(t.size, 2))); g4.appendChild(kv('Line height', t.lh === 'auto' ? 'Auto (' + fx(t.size * 1.2, 2) + ')' : fx(t.lh, 2), t.lh === 'auto' ? fx(t.size * 1.2, 2) : fx(t.lh, 2)));
        g4.appendChild(kv('Spacing', fx(t.ls, 2))); g4.appendChild(kv('Align', t.align));
        st.body.appendChild(g4);
        if (t.chars) st.body.appendChild(h('button', {class: 'hdx-chars', type: 'button', title: 'Copy the text', text: t.chars.length > 300 ? t.chars.slice(0, 300) + '\u2026' : t.chars, on: {click: () => copyText(t.chars, 'Copied the text.')}}));
      }
    }
    const cols = coloursOf(ids);
    if (cols.length) {
      const sc = section('Colours'), list = h('div', {class: 'hdx-colors'});
      sc.head.appendChild(segOwn([['hex', 'HEX'], ['rgb', 'RGB'], ['hsl', 'HSL']], insp.color, v => { insp.color = v; lsSet('hd.inspect.color', v); again(); }, 'Colour format'));
      for (const c of cols) { const txt = colorText(c.c, insp.color), sw = h('span', {class: 'hd-sw hdx-sw'}); sw.style.background = cssColor(c.c);
        list.appendChild(h('button', {class: 'hdx-color', type: 'button', title: 'Copy ' + txt, on: {click: () => copyText(txt, 'Copied ' + txt + '.')}}, sw, h('span', {class: 'hdx-cv', text: txt}), h('span', {class: 'hdx-cw', text: c.where}))); }
      sc.body.appendChild(list);
    }
    const code = section('Code'), fn = CODE[insp.lang] || cssFor;
    let text = '';
    try { text = fn(id).replace(/\n+$/, ''); } catch (e) { text = '/* The code for this layer could not be written. */'; if (window.console) console.error(e); }
    code.head.appendChild(segOwn([['css', 'CSS'], ['flutter', 'Flutter'], ['tailwind', 'Tailwind']], insp.lang, v => { insp.lang = v; lsSet('hd.inspect.code', v); again(); }, 'Code language'));
    if (ids.length > 1) code.body.appendChild(h('p', {class: 'hd-note', text: 'Showing the first of ' + ids.length + ' layers. Copy takes them all.'}));
    code.body.appendChild(h('pre', {class: 'hdx-code', tabIndex: 0, 'aria-label': CODE_LABEL[insp.lang] + ' code'}, h('code', {text: text})));
    code.body.appendChild(h('button', {class: 'hd-btn hdx-wide hdx-copy', type: 'button', text: 'Copy ' + CODE_LABEL[insp.lang], on: {click: () => copyCode(insp.lang, ids)}}));
    const assets = assetsOf(ids), sa = section('Assets', [{icon: 'export', title: 'Export\u2026', run: () => exportDialog(ids)}]);
    if (!assets.length) sa.body.appendChild(h('p', {class: 'hd-note', text: 'No layer here has export settings yet. Use Export to save this selection as PNG, JPG, SVG or PDF.'}));
    else {
      for (const a of assets) sa.body.appendChild(h('div', {class: 'hdx-asset'}, h('span', {class: 'hdx-aname', text: a.name, title: a.name}), h('span', {class: 'hdx-ameta', text: a.rows.length ? a.rows.map(r => r.fmt.toUpperCase() + ' ' + sizeLabel(r)).join(', ') : 'Picture'}),
        ib('export', 'Export \u201C' + a.name + '\u201D', () => exportNow([a.id]), 'sm')));
      if (assets.length > 1) sa.body.appendChild(h('button', {class: 'hd-btn hdx-wide', type: 'button', text: 'Export all ' + assets.length + ' assets', on: {click: () => exportNow(assets.map(a => a.id))}}));
    }
  }

  /* ================================================================ wiring: hooks, menus, keys, drop and paste */
  function typing(t) { return !!(t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)); }
  function dropPoint(ev) {
    const cv = HD.tools && HD.tools.canvas;
    if (!cv) return null;
    const r = cv.getBoundingClientRect();
    if (ev.clientX < r.left || ev.clientX > r.right || ev.clientY < r.top || ev.clientY > r.bottom) return null;
    const w = R().screenToWorld(ev.clientX - r.left, ev.clientY - r.top);
    return {x: w[0], y: w[1]};
  }
  function onDrop(ev) {
    const dt = ev.dataTransfer, files = dt ? Array.from(dt.files || []) : [];
    if (!files.length) return;
    const copies = files.filter(isCopyFile), rest = files.filter(f => !isCopyFile(f) && (isSvgFile(f) || isRaster(f)));
    if (!copies.length && !rest.length) return;
    ev.preventDefault(); ev.stopImmediatePropagation();
    if (copies.length) { importCopy(copies[0]); return; }
    if (!UI().mounted) return;
    if (!canEdit()) { toast('This file is view only.'); return; }
    placeFiles(rest, dropPoint(ev));
  }
  function onPaste(ev) {
    if (!UI() || !UI().mounted || document.querySelector('.hd-modal') || typing(ev.target)) return;
    const cd = ev.clipboardData, files = cd ? Array.from(cd.files || []).filter(f => isSvgFile(f) || isRaster(f)) : [];
    if (!files.length) return;                                  /* text (SVG text too) goes the usual way and reaches importSvg through the hook */
    ev.preventDefault(); ev.stopImmediatePropagation();
    if (!canEdit()) { toast('This file is view only.'); return; }
    placeFiles(files, null);
  }
  let lateDone = false;
  function lateCommands() {
    if (lateDone) return;
    lateDone = true;
    const c = UI().command, has = () => (HD.sel.ids || []).some(id => node(id));
    c({id: 'copyPng', label: 'Copy as PNG', group: 'Edit', keys: 'mod+shift+c', run: () => { copyPng(); }});
    c({id: 'copySvg', label: 'Copy as SVG', group: 'Edit', when: has, run: () => { copySvg(); }});
    c({id: 'copyCss', label: 'Copy as CSS', group: 'Edit', when: has, run: () => { copyCode('css'); }});
    c({id: 'copyFlutter', label: 'Copy as Flutter', group: 'Edit', when: has, run: () => { copyCode('flutter'); }});
    c({id: 'copyTailwind', label: 'Copy as Tailwind', group: 'Edit', when: has, run: () => { copyCode('tailwind'); }});
    c({id: 'placeImage', label: 'Place an image or SVG\u2026', group: 'Other', keys: 'mod+shift+k', edit: true, run: () => { pickAndPlace('any'); }});
    c({id: 'importSvgFile', label: 'Import an SVG file\u2026', group: 'Other', edit: true, run: () => { pickAndPlace('svg'); }});
    c({id: 'saveCopy', label: 'Save a copy as .hoola.json', group: 'Other', run: () => { saveCopy().catch(e => toast((e && e.message) || 'The copy could not be saved.', true)); }});
    c({id: 'importCopy', label: 'Import a .hoola.json into a new file\u2026', group: 'Other', run: () => { pickCopy(); }});
    c({id: 'inspect', label: 'Show the Inspect panel', group: 'View', run: () => { const st = UI().state; st.rightTab = 'inspect'; st.sig = ''; UI().refresh(); }});
  }
  function setup() {
    const ui = UI();
    if (!ui || !ui.hook) return;
    ui.hook('export', ids => exportDialog(ids));
    ui.hook('exportSection', exportSection);
    ui.hook('importSvg', (text, at) => { importSvg(text, at && isFinite(at.x) ? {x: at.x, y: at.y} : null, {page: at && at.page}); });
    ui.registerPanel('right', 'inspect', {title: 'Inspect', render: inspectRender});
    ui.registerShortcut('mod+shift+c', () => { copyPng(); }, 'Copy as PNG');
    ui.registerShortcut('mod+shift+k', () => { if (canEdit()) pickAndPlace('any'); else toast('This file is view only.'); }, 'Place an image or SVG');
    ui.registerMenu('context', ids => (ids && ids.length ? {label: 'Copy as PNG', keys: 'mod+shift+c', run: () => { copyPng(ids); }} : null));
    ui.registerMenu('context', ids => (ids && ids.length ? {label: 'Copy as SVG', run: () => { copySvg(ids); }} : null));
    ui.registerMenu('context', ids => (ids && ids.length ? {label: 'Copy as code', sub: [{label: 'CSS', run: () => { copyCode('css', ids); }}, {label: 'Flutter', run: () => { copyCode('flutter', ids); }}, {label: 'Tailwind', run: () => { copyCode('tailwind', ids); }}]} : null));
    ui.registerMenu('context', ids => (ids && !ids.length && canEdit() ? {label: 'Place an image or SVG\u2026', keys: 'mod+shift+k', run: () => { pickAndPlace('any'); }} : null));
    ui.registerMenu('main', {label: 'Place an image or SVG\u2026', icon: 'image', keys: 'mod+shift+k', run: () => { if (canEdit()) pickAndPlace('any'); else toast('This file is view only.'); }});
    ui.registerMenu('main', {label: 'Save a copy (.hoola.json)', icon: 'export', run: () => { saveCopy().catch(e => toast((e && e.message) || 'The copy could not be saved.', true)); }});
    ui.registerMenu('main', {label: 'Import a copy (.hoola.json)\u2026', icon: 'copy', run: () => { pickCopy(); }});
    /* the palette commands go in after the editor's own (it only adds its own while the list is still empty) */
    const mount0 = ui.mount;
    if (typeof mount0 === 'function') ui.mount = function () { const r = mount0.apply(this, arguments); try { lateCommands(); } catch (e) { if (window.console) console.error(e); } return r; };
    if (ui.mounted) lateCommands();
    if (S() && S().on) S().on('change', () => { insp.ver++; if (sec.el && sec.el.isConnected) schedulePreview(350); });
    if (S() && S().on) S().on('load', () => { insp.ver++; });
    window.addEventListener('dragover', ev => { const t = ev.dataTransfer && ev.dataTransfer.types; if (t && Array.from(t).indexOf('Files') >= 0) ev.preventDefault(); }, true);
    window.addEventListener('drop', onDrop, true);
    document.addEventListener('paste', onPaste, true);
  }

  HD.handoff = {
    /* export */
    FORMATS: FORMATS.map(f => f[0]), LIMIT_SIDE: LIMIT_SIDE, crc32: crc32, zip: zip, pdf: pdf, jpegInfo: jpegInfo, safeName: safeName, parseSize: parseSize,
    rowsOf: rowsOf, sizeFor: sizeFor, plan: plan, renderOne: renderOne, runPlan: runPlan, combinedPdf: combinedPdf, exportNow: exportNow, exportDialog: exportDialog, download: download,
    copyPng: copyPng, copySvg: copySvg, selectionCanvas: selectionCanvas, selectionSvg: selectionSvg,
    /* import */
    svgRead: svgRead, importSvg: importSvg, importImages: importImages, placeFiles: placeFiles, pickAndPlace: pickAndPlace, parsePathD: parsePathD, parseTransform: parseTransform, parseColor: parseColor, decomp: decomp,
    /* inspect */
    code: {css: cssFor, cssPairs: cssPairs, flutter: flutterFor, tailwind: tailwindFor, tailwindClasses: tailwindClasses, gradient: cssGradient}, colorText: colorText, copyCode: copyCode, look: look,
    /* file */
    saveCopy: saveCopy, importCopy: importCopy, sendDocument: sendDocument
  };
  setup();
})();

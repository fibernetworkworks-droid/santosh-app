/* HOOLA DESIGN - D9b speed harness, against a REAL server (docs/HOOLA_DESIGN_PLAN.md section 8, D9b).
   Files of 5,000 / 20,000 / 100,000 layers (10 pages, mixed layer types, instances of a component that lives on
   page 1) are made through the server's own room. Then it MEASURES and prints a table:
     open        server -> first paint in a real editor (headless Chromium, 1280 x 800), whole file vs page by page,
                 and when every page is in; the JS heap after a GC
     index       HD.index on 100,000 layers on ONE page: build, a viewport query, a point query, a frame move;
                 the grid against the R-tree; and the editor's own hitTest beside index.at
     layout      HD.layout.run on a big auto-layout tree (to decide whether a layout worker would earn its keep)
     round trip  op -> ack and op -> the other two editors, p50 / p95, three clients, JSON and c1
     wire        bytes of a 1,000-op batch and its parse time, JSON vs c1
   and asserts BUDGETS (set from these measurements with headroom), so a regression fails.

   Run:  HD_BASE=http://127.0.0.1:<port> HD_KEY=<api key> node server/tests/web/design_perf_test.js
         (server/tests/test_v0825_design_speed.py starts the server on a free port with a fresh database)
         HD_PERF_SIZES=5000,20000 for a quick run (the 100k checks are then skipped).
   Exit 0 = pass, 1 = fail, 77 = could not run here (no playwright / no Chromium / no server). Last line = JSON. */
'use strict';
const assert = require('node:assert/strict'), fs = require('fs'), path = require('path'), vm = require('vm');
const BASE = (process.env.HD_BASE || '').replace(/\/+$/, ''), KEY = process.env.HD_KEY || 'itest-key';
const SIZES = (process.env.HD_PERF_SIZES || '5000,20000,100000').split(',').map(Number).filter(n => n > 0);
const DIR = path.resolve(__dirname, '../../app/static/console/design');
let checks = 0;
const ok = (cond, what) => { assert.ok(cond, what); checks++; };
const fmt = (v, d) => (v === null || v === undefined || Number.isNaN(v)) ? '-' : (typeof v === 'number' ? v.toFixed(d === undefined ? 1 : d) : String(v));
const pct = (arr, p) => { const a = arr.slice().sort((x, y) => x - y); return a.length ? a[Math.min(a.length - 1, Math.floor(a.length * p))] : null; };
const sleep = ms => new Promise(r => setTimeout(r, ms));

/* The BUDGETS: about 3 x what this harness measured on the 4-core sandbox (headless, software raster). */
const BUDGET = {
  open100kLazyMs: 4000,          /* page by page: the first page painted */
  lazyVsFullMax: 0.75,           /* page by page must open in at most 3/4 of the whole-file time at 100k */
  indexBuild100kMs: 1500,        /* one page of 100,000 layers, bulk */
  indexQueryUs: 300,             /* a 1280 x 800 viewport */
  indexAtUs: 60,                 /* a point */
  indexMoveUs: 3000,             /* a frame with its children moves, worked in */
  layoutRunMs: 50,               /* one edit inside a 12,000-layer auto-layout tree */
  rtt50Ms: 25, rtt95Ms: 80,      /* op -> ack, op -> the others */
  c1BytesMax: 0.85,              /* c1 <= 85 % of the JSON bytes of a 1,000-op batch */
  c1ParseMax: 1.6                /* c1 parse + decode <= 1.6 x JSON.parse of the JSON frame */
};

async function rest(method, p, body) {
  const headers = {Authorization: 'Bearer ' + KEY};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const r = await fetch(BASE + '/api/design' + p, {method, headers, body: body === undefined ? undefined : JSON.stringify(body)});
  const text = await r.text();
  let data = null; try { data = JSON.parse(text); } catch (e) { data = text; }
  return {status: r.status, data};
}

/* ------------------------------------------------------------------ the codec, from hd-net.js itself */
function codec() {
  const ctx = {console, setTimeout, clearTimeout, setInterval, clearInterval, location: {protocol: 'http:', host: 'x'}, localStorage: {getItem: () => null}, addEventListener() {}};
  ctx.window = ctx;
  vm.createContext(ctx);
  for (const f of ['hd-math.js', 'hd-core.js', 'hd-net.js']) vm.runInContext(fs.readFileSync(path.join(DIR, f), 'utf8'), ctx, {filename: f});
  return ctx.HD.net.codec;
}

/* ------------------------------------------------------------------ a file of N layers, 10 pages, mixed */
function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
function genOps(N, cid, pages) {
  const rnd = rng(N), ops = [], solid = c => [{type: 'solid', color: c, opacity: 1, visible: true}];
  let n = 0, made = 0;
  const id = () => cid + ':' + (++n);
  const add = (p) => { const nid = id(); ops.push({id: nid, p}); made++; return nid; };
  const COL = ['#6E55F0', '#F24E1E', '#0FA958', '#1ABCFE', '#FFC700', '#111111', '#FFFFFF'];
  const pageIds = ['0:1'];
  for (let i = 1; i < pages; i++) pageIds.push(add({type: 'PAGE', parent: '0:0', idx: 'b' + i, name: 'Page ' + (i + 1)}));
  const comp = add({type: 'COMPONENT', parent: '0:1', idx: 'a0', name: 'Card', x: -600, y: 0, w: 240, h: 120, fills: solid('#FFFFFF'), radius: 12});
  add({type: 'RECT', parent: comp, idx: 'a0', name: 'Bar', x: 12, y: 12, w: 216, h: 24, fills: solid('#6E55F0')});
  add({type: 'TEXT', parent: comp, idx: 'a1', name: 'Title', x: 12, y: 48, w: 180, h: 20, chars: 'Diwali sale', fontSize: 16});
  const per = Math.floor((N - made) / pages);
  pageIds.forEach((pg, pi) => {
    let onPage = 0, fi = 0;
    while (onPage < per) {
      const fx = (fi % 25) * 460, fy = Math.floor(fi / 25) * 360, auto = fi % 4 === 0;
      const f = add({type: 'FRAME', parent: pg, idx: 'a' + String(fi).padStart(4, '0'), name: 'Frame ' + fi, x: fx, y: fy, w: 420, h: 320,
        fills: solid(COL[fi % COL.length]), layout: auto ? {mode: 'v', gap: 8, pad: [12, 12, 12, 12], alignMain: 'start', alignCross: 'start', wrap: false} : undefined});
      onPage++; fi++;
      for (let k = 0; k < 19 && onPage < per; k++) {
        const kind = k % 7, x = Math.floor(rnd() * 360), y = Math.floor(rnd() * 270), idx = 'a' + String(k).padStart(2, '0');
        let p;
        if (kind === 0) p = {type: 'RECT', w: 20 + Math.floor(rnd() * 60), h: 10 + Math.floor(rnd() * 40), radius: 4, fills: solid(COL[k % COL.length])};
        else if (kind === 1) p = {type: 'TEXT', w: 120, h: 18, chars: 'Label ' + k, fontSize: 14};
        else if (kind === 2) p = {type: 'ELLIPSE', w: 24, h: 24, fills: solid('#FFC700'), strokes: solid('#111111'), strokeWeight: 2};
        else if (kind === 3) p = {type: 'STAR', w: 30, h: 30, fills: solid('#F24E1E')};
        else if (kind === 4) p = {type: 'VECTOR', w: 40, h: 20, path: 'M0 0 L40 0 L20 20 Z', fills: solid('#0FA958')};
        else if (kind === 5) p = {type: 'INSTANCE', w: 240, h: 120, comp};
        else p = {type: 'LINE', w: 80, h: 0, strokes: solid('#111111')};
        Object.assign(p, {parent: f, idx, name: p.type.toLowerCase() + ' ' + k, x, y});
        if (p.layout === undefined) delete p.layout;
        add(p); onPage++;
      }
    }
  });
  for (const op of ops) for (const k in op.p) if (op.p[k] === undefined) delete op.p[k];
  return ops;
}

function sock(params, extra) {
  return new Promise((resolve, reject) => {
    const url = BASE.replace(/^http/, 'ws') + '/api/design/ws?' + params;
    const ws = new WebSocket(url, ['hoola', 'hoola-key.' + KEY]);
    const c = {ws, frames: [], waiters: [], bytes: 0, init: null};
    ws.onmessage = ev => {
      const text = typeof ev.data === 'string' ? ev.data : Buffer.from(ev.data).toString();
      c.bytes += text.length;
      const msg = JSON.parse(text), at = performance.now();
      if (!c.init && msg.t === 'init') { c.init = msg; c.initText = text; resolve(c); return; }
      const w = c.waiters.slice();
      for (const fn of w) fn(msg, at, text);
    };
    ws.onerror = e => reject(new Error('socket error ' + (e.message || '')));
    ws.onclose = ev => { if (!c.init) reject(new Error('socket closed ' + ev.code)); };
    if (extra) extra(c);
  });
}
function waitFor(c, test, ms) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => { c.waiters.splice(c.waiters.indexOf(fn), 1); reject(new Error('timed out waiting')); }, ms || 30000);
    const fn = (msg, at, text) => { if (test(msg)) { clearTimeout(t); c.waiters.splice(c.waiters.indexOf(fn), 1); resolve({msg, at, text}); } };
    c.waiters.push(fn);
  });
}
const isAck = n => m => (m.t === 'ack' && m.n === n) || (Array.isArray(m) && m[0] === 3 && m[1] === n);
const isOps = m => m.t === 'ops' || (Array.isArray(m) && m[0] === 2);

async function makeFile(N) {
  const file = (await rest('POST', '/files', {name: 'Perf ' + N})).data;
  const c = await sock('file=' + encodeURIComponent(file.id));
  const ops = genOps(N, c.init.cid, 10);
  let n = 0, i = 0;
  const pending = [];
  while (i < ops.length) {
    const part = [];
    let chars = 0;
    while (i < ops.length && part.length < 1000 && chars < 400000) { const s = JSON.stringify(ops[i]); chars += s.length; part.push(ops[i]); i++; }
    const no = ++n;
    pending.push(waitFor(c, isAck(no), 120000).then(r => { assert.deepEqual(r.msg.rejected, [], 'a seed op was refused'); }));
    c.ws.send(JSON.stringify({t: 'ops', n: no, ops: part}));
    if (pending.length >= 4) await pending.shift();
  }
  await Promise.all(pending);
  c.ws.close();
  for (let t = 0; t < 200; t++) {                                  /* the room checkpoints when the last one leaves */
    const f = (await rest('GET', '/files/' + file.id)).data;
    if (f && f.nodes >= ops.length) break;
    await sleep(250);
  }
  return {id: file.id, nodes: ops.length + 2, pages: 10};
}

async function main() {
  if (!BASE) { console.log('SKIP: HD_BASE is not set (run it through test_v0825_design_speed.py)'); process.exit(77); }
  let chromium;
  try { ({chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright')); } catch (e) { console.log('SKIP: playwright is not installed'); process.exit(77); }
  try { const r = await fetch(BASE + '/console/design'); if (r.status !== 200) throw new Error('status ' + r.status); } catch (e) { console.log('SKIP: no Hoola Design server at ' + BASE + ' (' + e.message + ')'); process.exit(77); }
  let browser;
  try { browser = await chromium.launch({executablePath: process.env.HOOLA_CHROMIUM || process.env.CHROMIUM_EXECUTABLE || undefined, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage', '--js-flags=--expose-gc']}); }
  catch (e) { console.log('SKIP: Chromium can not start here: ' + String(e.message).split('\n')[0]); process.exit(77); }
  const out = {sizes: {}, index: null, layout: null, rtt: {}, wire: null};
  const errors = [];
  try {
    /* ------------------------------------------------------------ files */
    const files = {};
    for (const N of SIZES) { const t0 = performance.now(); files[N] = await makeFile(N); files[N].seedS = (performance.now() - t0) / 1000; }

    /* ------------------------------------------------------------ open: server -> first paint */
    const ctx = await browser.newContext({viewport: {width: 1280, height: 800}});
    const page = await ctx.newPage();
    page.on('pageerror', e => errors.push(e.message));
    await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, r => r.fulfill({contentType: 'text/css', body: ''}));
    await page.addInitScript(key => { localStorage.setItem('hoola.console.token', key); }, KEY);
    await page.goto(BASE + '/console/design#/');
    await page.waitForFunction(() => window.HD && HD.net && HD.render && HD.app, null, {timeout: 30000});
    for (const N of SIZES) {
      const row = out.sizes[N] = {nodes: files[N].nodes};
      for (const lazy of [false, true]) {
        const r = await page.evaluate(([id, lazy]) => new Promise(done => {
          if (window.gc) window.gc();
          HD.net.options.lazy = lazy;
          const t0 = performance.now(), frames0 = HD.render.stats.frames, bytes0 = HD.net.wire.bytesIn;
          let tInit = null, tPaint = null, tAll = null, gotInit = false;
          const offI = HD.net.on('init', () => { gotInit = true; tInit = performance.now() - t0; });
          const tick = () => {
            const now = performance.now() - t0;
            if (gotInit && tPaint === null && HD.ui.mounted && HD.render.stats.frames > frames0 && HD.store.count() > 2) tPaint = now;
            if (tPaint !== null && tAll === null && HD.net.loading().length === 0 && HD.net.pending() === 0) tAll = now;
            if ((tAll !== null) || now > 120000) {
              offI();
              if (window.gc) window.gc();
              done({init: tInit, paint: tPaint, all: tAll, nodes: HD.store.count(), heapMB: performance.memory ? performance.memory.usedJSHeapSize / 1048576 : null,
                bytes: HD.net.wire.bytesIn - bytes0, partial: lazy && HD.net.pages !== null});
              return;
            }
            requestAnimationFrame(tick);
          };
          location.hash = '#/f/' + id;
          requestAnimationFrame(tick);
        }), [files[N].id, lazy]);
        row[lazy ? 'lazy' : 'full'] = r;
        if (lazy && N === Math.max.apply(null, SIZES)) {
          out.hit = await page.evaluate(() => {             /* the editor's own hit test beside HD.index.at, on the page she sees */
            const S = HD.store, pg = HD.sel.page, b = S.worldBounds(pg);
            let s = 5; const r = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
            const pts = []; for (let i = 0; i < 400; i++) pts.push([b.x + r() * b.w, b.y + r() * b.h]);
            HD.index.at(0, 0, pg);
            let t = performance.now(), a = 0, c = 0;
            for (const p of pts) if (HD.render.hitTest(p[0], p[1], {deep: true})) a++;
            const hit = (performance.now() - t) / pts.length * 1000;
            t = performance.now();
            for (const p of pts) if (HD.index.at(p[0], p[1], pg, {visible: true}).length) c++;
            return {layers: S.children(pg).length, hitTestUs: hit, indexAtUs: (performance.now() - t) / pts.length * 1000, hits: a, indexHits: c};
          });
        }
        await page.evaluate(() => { location.hash = '#/'; });
        await page.waitForFunction(() => HD.net.status === 'offline' || HD.net.file === null, null, {timeout: 20000});
        await sleep(300);
      }
      ok(row.full.nodes === row.lazy.nodes && row.full.nodes >= files[N].nodes - 2, N + ': both ways end with the whole file (' + row.full.nodes + ' / ' + row.lazy.nodes + ')');
    }

    /* ------------------------------------------------------------ the index + layout + parse, in a page of their own */
    const bench = await ctx.newPage();
    bench.on('pageerror', e => errors.push('bench: ' + e.message));
    await bench.goto(BASE + '/console/design#/');
    await bench.waitForFunction(() => window.HD && HD.index && HD.layout && HD.net && HD.net.codec, null, {timeout: 30000});
    out.index = await bench.evaluate(() => {
      const S = HD.store, I = HD.index, res = {};
      let s = 9; const r = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
      const nodes = {'0:0': {type: 'DOCUMENT', name: 'D'}, '0:1': {type: 'PAGE', parent: '0:0', idx: 'a0', name: 'P'}};
      let n = 100;
      for (let f = 0; f < 5000; f++) {
        const fid = '1:' + (n++);
        nodes[fid] = {type: 'FRAME', parent: '0:1', idx: 'a' + f, name: 'F', x: (f % 70) * 460, y: Math.floor(f / 70) * 360, w: 420, h: 320, rot: f % 23 === 0 ? 15 : 0};
        for (let k = 0; k < 19; k++) nodes['1:' + (n++)] = {type: ['RECT', 'TEXT', 'ELLIPSE'][k % 3], parent: fid, idx: 'a' + k, name: 'R', x: Math.floor(r() * 380), y: Math.floor(r() * 280), w: 20 + Math.floor(r() * 40), h: 10 + Math.floor(r() * 30)};
      }
      const W = 70 * 460, H = Math.ceil(5000 / 70) * 360;
      const one = (eng) => {
        HD.net.close();
        S.load(JSON.parse(JSON.stringify({nodes})), 5);
        HD.sel.setPage('0:1');
        I.engine(eng);
        S.walk('0:1', id => { S.worldBounds(id); });                   /* the store's matrices are warm, as in the editor */
        let t = performance.now(); I.query({x: 0, y: 0, w: 1, h: 1}, '0:1'); const build = performance.now() - t;
        let hits = 0; t = performance.now();
        for (let i = 0; i < 2000; i++) hits += I.query({x: r() * W, y: r() * H, w: 1280, h: 800}, '0:1').length;
        const q = (performance.now() - t) / 2000 * 1000;
        t = performance.now();
        for (let i = 0; i < 5000; i++) I.at(r() * W, r() * H, '0:1');
        const at = (performance.now() - t) / 5000 * 1000;
        const frames = S.children('0:1');
        let tm = 0;
        for (let i = 0; i < 300; i++) { const f = frames[Math.floor(r() * frames.length)]; S.set(f, {x: Math.floor(r() * W)}); const t1 = performance.now(); I.at(1, 1, '0:1'); tm += performance.now() - t1; }
        /* correct: the same answer as looking at every layer */
        let wrong = 0;
        for (let i = 0; i < 30; i++) {
          const rect = {x: r() * W, y: r() * H, w: 2000, h: 1500}, a = new Set(I.query(rect, '0:1'));
          let b = 0;
          S.walk('0:1', id => { if (id === '0:1') return true; const bb = S.worldBounds(id); if (bb.x <= rect.x + rect.w && bb.x + bb.w >= rect.x && bb.y <= rect.y + rect.h && bb.y + bb.h >= rect.y) { b++; if (!a.has(id)) wrong++; } return true; });
          if (b !== a.size) wrong++;
        }
        return {build, queryUs: q, avgHits: hits / 2000, atUs: at, moveUs: tm / 300 * 1000, wrong, nodes: S.count() - 2};
      };
      res.grid = one('grid');
      res.rtree = one('rtree');
      I.engine('grid');
      return res;
    });
    ok(out.index.grid.wrong === 0 && out.index.rtree.wrong === 0, 'the index answers exactly what a look at every layer answers (grid ' + out.index.grid.wrong + ', rtree ' + out.index.rtree.wrong + ')');

    out.layout = await bench.evaluate(() => {
      const S = HD.store, nodes = {'0:0': {type: 'DOCUMENT', name: 'D'}, '0:1': {type: 'PAGE', parent: '0:0', idx: 'a0', name: 'P'}};
      let n = 100;
      const top = '1:' + (n++);
      nodes[top] = {type: 'FRAME', parent: '0:1', idx: 'a0', name: 'List', x: 0, y: 0, w: 600, h: 100, sizeV: 'hug', layout: {mode: 'v', gap: 4, pad: [8, 8, 8, 8], alignMain: 'start', alignCross: 'stretch', wrap: false}};
      const rows = [];
      for (let i = 0; i < 2000; i++) {
        const row = '1:' + (n++); rows.push(row);
        nodes[row] = {type: 'FRAME', parent: top, idx: 'a' + String(i).padStart(4, '0'), name: 'Row', w: 580, h: 40, sizeH: 'fill', sizeV: 'hug', layout: {mode: 'h', gap: 8, pad: [4, 4, 4, 4], alignMain: 'start', alignCross: 'center', wrap: false}};
        for (let k = 0; k < 5; k++) nodes['1:' + (n++)] = {type: 'RECT', parent: row, idx: 'a' + k, name: 'Cell', w: 60 + k * 10, h: 24};
      }
      HD.net.close();
      S.load({nodes}, 5);
      S.tx('first', () => { HD.layout.run(new Set([top]), new Map()); });
      const kidsOf = row => S.children(row);
      let worst = 0, sum = 0;
      for (let i = 0; i < 40; i++) {
        const row = rows[Math.floor(i * 49.7) % rows.length], cell = kidsOf(row)[2];
        const t = performance.now();
        S.set(cell, {w: 60 + (i % 7) * 13, h: 20 + (i % 5) * 6});         /* the tx runs HD.layout.run: the row hugs, the list grows */
        const d = performance.now() - t; sum += d; if (d > worst) worst = d;
      }
      const t = performance.now();
      S.set(top, {layout: {mode: 'v', gap: 6, pad: [8, 8, 8, 8], alignMain: 'start', alignCross: 'stretch', wrap: false}});   /* every row moves */
      return {nodes: S.count() - 2, editAvgMs: sum / 40, editWorstMs: worst, relayoutAllMs: performance.now() - t};
    });

    /* ------------------------------------------------------------ the wire: a 1,000-op batch */
    const C = codec();
    const batchOps = genOps(1100, 77, 1).slice(100).map((op, i) => i % 3 === 0 ? op : {id: op.id, p: i % 3 === 1 ? {x: op.p.x + 0.5, y: op.p.y} : {fills: op.p.fills || [{type: 'solid', color: '#123456', opacity: 1, visible: true}], name: 'n' + i}});
    const jsonFrame = JSON.stringify({t: 'ops', seq: 99, by: 4, ops: batchOps});
    const c1Frame = JSON.stringify([2, 99, 4, batchOps.map(C.encOp)]);
    out.wire = await bench.evaluate(([j, c]) => {
      const D = HD.net.codec, R = 300;
      let t = performance.now(); for (let i = 0; i < R; i++) JSON.parse(j); const pj = (performance.now() - t) / R;
      t = performance.now(); for (let i = 0; i < R; i++) D.decFrame(JSON.parse(c)); const pc = (performance.now() - t) / R;
      const back = D.decFrame(JSON.parse(c)), want = JSON.parse(j);
      return {jsonBytes: j.length, c1Bytes: c.length, jsonParseMs: pj, c1ParseMs: pc, same: JSON.stringify(back.ops) === JSON.stringify(want.ops)};
    }, [jsonFrame, c1Frame]);
    ok(out.wire.same, 'a c1 batch decodes to exactly the JSON batch');

    /* ------------------------------------------------------------ round trip: three clients, JSON and c1 */
    const rttN = SIZES.includes(20000) ? 20000 : SIZES[0];
    for (const enc of ['json', 'c1']) {
      const q = 'file=' + encodeURIComponent(files[rttN].id) + (enc === 'c1' ? '&enc=c1' : '');
      const [a, b, c] = [await sock(q), await sock(q), await sock(q)];
      ok(enc === 'json' ? a.init.use === undefined : a.init.use === 'c1', enc + ': the server agreed on the encoding');
      const target = Object.keys(a.init.doc.nodes).find(k => a.init.doc.nodes[k].type === 'RECT');
      const ack = [], fan = [];
      let wireUp = 0;
      for (let i = 0; i < 300; i++) {
        const no = i + 1, op = {id: target, p: {x: i, y: i * 2}};
        const frame = enc === 'c1' ? JSON.stringify([1, no, [C.encOp(op)]]) : JSON.stringify({t: 'ops', n: no, ops: [op]});
        wireUp += frame.length;
        const pa = waitFor(a, isAck(no)), pb = waitFor(b, isOps), pc = waitFor(c, isOps);
        const t0 = performance.now();
        a.ws.send(frame);
        const [ra, rb, rc] = await Promise.all([pa, pb, pc]);
        ack.push(ra.at - t0); fan.push(Math.max(rb.at, rc.at) - t0);
        if (i === 0) { const m = rb.msg; ok(enc === 'c1' ? Array.isArray(m) : m.t === 'ops', enc + ': the others hear it in ' + enc); }
      }
      out.rtt[enc] = {ack50: pct(ack, 0.5), ack95: pct(ack, 0.95), fan50: pct(fan, 0.5), fan95: pct(fan, 0.95), upBytes: wireUp / 300};
      for (const s of [a, b, c]) s.ws.close();
      await sleep(200);
    }
  } finally {
    await browser.close();
  }

  /* ------------------------------------------------------------ the table */
  const L = [];
  L.push('HOOLA DESIGN D9b speed (headless Chromium 1280x800, ' + require('os').cpus().length + ' cores)');
  L.push('');
  L.push('open (server -> first paint)      | layers  | whole file: init / paint / heap | page by page: init / paint / all pages / heap | bytes whole -> first');
  for (const N of SIZES) {
    const r = out.sizes[N];
    L.push('  ' + String(N).padEnd(32) + ' | ' + String(r.nodes).padEnd(7) + ' | ' + fmt(r.full.init, 0) + ' / ' + fmt(r.full.paint, 0) + ' ms / ' + fmt(r.full.heapMB) + ' MB' +
      '        | ' + fmt(r.lazy.init, 0) + ' / ' + fmt(r.lazy.paint, 0) + ' / ' + fmt(r.lazy.all, 0) + ' ms / ' + fmt(r.lazy.heapMB) + ' MB' + (r.lazy.partial ? '' : ' (whole: under the threshold)') +
      ' | ' + fmt(r.full.bytes / 1024, 0) + ' KB -> ' + fmt(r.lazy.bytes / 1024, 0) + ' KB');
  }
  const ix = out.index;
  L.push('');
  L.push('index, 100,000 layers on ONE page | build ms | viewport query us (hits) | point us | frame move us');
  for (const k of ['grid', 'rtree']) L.push('  ' + k.padEnd(32) + ' | ' + fmt(ix[k].build).padEnd(8) + ' | ' + fmt(ix[k].queryUs) + ' (' + fmt(ix[k].avgHits, 0) + ')' + ''.padEnd(10) + ' | ' + fmt(ix[k].atUs, 2) + '     | ' + fmt(ix[k].moveUs, 0));
  if (out.hit) L.push('  hit test on the ' + Math.max.apply(null, SIZES) + '-layer file (her page): HD.render.hitTest ' + fmt(out.hit.hitTestUs, 0) + ' us vs HD.index.at ' + fmt(out.hit.indexAtUs, 1) + ' us (' + out.hit.hits + ' / ' + out.hit.indexHits + ' of 400 points hit)');
  L.push('');
  L.push('layout: ' + out.layout.nodes + ' layers of auto layout - one edit ' + fmt(out.layout.editAvgMs, 2) + ' ms avg / ' + fmt(out.layout.editWorstMs, 2) + ' ms worst, every row moved ' + fmt(out.layout.relayoutAllMs, 1) + ' ms');
  L.push('');
  L.push('round trip (' + (SIZES.includes(20000) ? '20,000' : SIZES[0]) + '-layer file, 3 clients, 300 ops) | ack p50 / p95 | others p50 / p95 | bytes up per op frame');
  for (const k of ['json', 'c1']) { const t = out.rtt[k]; L.push('  ' + k.padEnd(32) + ' | ' + fmt(t.ack50, 2) + ' / ' + fmt(t.ack95, 2) + ' ms | ' + fmt(t.fan50, 2) + ' / ' + fmt(t.fan95, 2) + ' ms | ' + fmt(t.upBytes, 0)); }
  L.push('');
  const w = out.wire;
  L.push('wire, one 1,000-op batch           | JSON ' + w.jsonBytes + ' bytes, parse ' + fmt(w.jsonParseMs, 3) + ' ms | c1 ' + w.c1Bytes + ' bytes (' + fmt(100 * w.c1Bytes / w.jsonBytes, 0) + ' %), parse + decode ' + fmt(w.c1ParseMs, 3) + ' ms');
  console.log(L.join('\n'));

  /* ------------------------------------------------------------ the budgets */
  if (SIZES.includes(100000)) {
    const r = out.sizes[100000];
    ok(r.lazy.partial, '100k: it opened page by page');
    ok(r.lazy.paint < BUDGET.open100kLazyMs, '100k page by page: first paint ' + fmt(r.lazy.paint, 0) + ' ms < ' + BUDGET.open100kLazyMs);
    ok(r.lazy.paint < r.full.paint * BUDGET.lazyVsFullMax, '100k: page by page paints in ' + fmt(r.lazy.paint, 0) + ' ms, the whole file in ' + fmt(r.full.paint, 0) + ' ms');
  }
  for (const N of SIZES) ok(out.sizes[N].full.paint !== null && out.sizes[N].lazy.paint !== null, N + ': both opened');
  ok(ix.grid.build < BUDGET.indexBuild100kMs, 'index build ' + fmt(ix.grid.build) + ' ms');
  ok(ix.grid.queryUs < BUDGET.indexQueryUs, 'viewport query ' + fmt(ix.grid.queryUs) + ' us');
  ok(ix.grid.atUs < BUDGET.indexAtUs, 'point query ' + fmt(ix.grid.atUs, 2) + ' us');
  ok(ix.grid.moveUs < BUDGET.indexMoveUs, 'frame move ' + fmt(ix.grid.moveUs, 0) + ' us');
  ok(out.layout.editAvgMs < BUDGET.layoutRunMs, 'one layout edit ' + fmt(out.layout.editAvgMs, 2) + ' ms');
  for (const k of ['json', 'c1']) {
    ok(out.rtt[k].ack50 < BUDGET.rtt50Ms && out.rtt[k].fan50 < BUDGET.rtt50Ms, k + ' round trip p50 ' + fmt(out.rtt[k].ack50, 2) + ' / ' + fmt(out.rtt[k].fan50, 2) + ' ms');
    ok(out.rtt[k].ack95 < BUDGET.rtt95Ms && out.rtt[k].fan95 < BUDGET.rtt95Ms, k + ' round trip p95 ' + fmt(out.rtt[k].ack95, 2) + ' / ' + fmt(out.rtt[k].fan95, 2) + ' ms');
  }
  ok(w.c1Bytes < w.jsonBytes * BUDGET.c1BytesMax, 'c1 bytes ' + w.c1Bytes + ' vs JSON ' + w.jsonBytes);
  ok(w.c1ParseMs < w.jsonParseMs * BUDGET.c1ParseMax, 'c1 parse ' + fmt(w.c1ParseMs, 3) + ' vs JSON ' + fmt(w.jsonParseMs, 3) + ' ms');
  ok(!errors.length, 'no page errors: ' + errors.slice(0, 3).join(' | '));
  console.log(JSON.stringify({ok: true, checks, budget: BUDGET, out}));
}

main().catch(e => { console.error(e && e.stack || e); console.log(JSON.stringify({ok: false, error: String(e && e.message || e), checks})); process.exit(1); });

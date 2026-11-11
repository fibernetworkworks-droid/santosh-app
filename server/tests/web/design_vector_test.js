/* HOOLA DESIGN - browser walk of phase D2 "design depth" (hd-vector.js + the D2 parts of hd-render.js / hd-layout.js)
   in a REAL browser, against the real editor and the mock server of design_ui_test.js (no Python server needed).
   Run:  node server/tests/web/design_vector_test.js        (DESIGN_SHOTS=<dir> also writes screenshots)
   Exit 0 = pass, 1 = fail, 77 = could not run here (no playwright / no Chromium). The last line is a JSON report.
   Checked with the mouse and by reading canvas pixels: the path parser, vector edit mode (drag a point, add, delete,
   smooth, bend, close, one undo step a gesture, the box hugs the path and nothing else moves), Edit shape, the four
   boolean groups against a compositing reference, their stroke / hit test / SVG, Flatten, masks (clip + alpha),
   rulers, guides (pull, snap, remove), layout grids (panel, toggle, never in an export), gradient handles, the
   Alt distances, and the renderer / layout fixes (elliptical radial, text stroke inside / outside, shadow spread,
   paths that do not start at 0,0, instances laid out again, turned children in auto layout). Light and dark. */
'use strict';
const fs = require('fs'), path = require('path'), assert = require('node:assert/strict');
const {startMock, newDoc, layoutProblems} = require('./design_ui_test.js');
const solid = (c, o) => [{type: 'solid', color: c, opacity: o === undefined ? 1 : o, visible: true}];

function seed() {
  const doc = newDoc();
  Object.assign(doc.nodes, {
    '9:1': {type: 'FRAME', parent: '0:1', idx: 'a0', name: 'Board', x: 0, y: 0, w: 600, h: 400, fills: solid('#FFFFFF')},
    '9:2': {type: 'VECTOR', parent: '9:1', idx: 'a0', name: 'Blob', x: 40, y: 40, w: 120, h: 100, path: 'M0 50C0 20 30 0 60 0C90 0 120 20 120 50L120 100L0 100Z', fills: solid('#6E55F0')},
    '9:3': {type: 'RECT', parent: '9:1', idx: 'a1', name: 'A', x: 220, y: 40, w: 120, h: 100, radius: 16, fills: solid('#EE8F35')},
    '9:4': {type: 'ELLIPSE', parent: '9:1', idx: 'a2', name: 'B', x: 290, y: 90, w: 110, h: 110, fills: solid('#13875F')},
    '9:5': {type: 'RECT', parent: '9:1', idx: 'a3', name: 'Grad', x: 40, y: 220, w: 220, h: 120, fills: [{type: 'radial', stops: [{pos: 0, color: '#FFFFFF', opacity: 1}, {pos: 1, color: '#0000FF', opacity: 1}], from: [0.5, 0.5], to: [1, 0.5], opacity: 1, visible: true}]},
    '9:6': {type: 'STAR', parent: '9:1', idx: 'a4', name: 'Star', x: 440, y: 230, w: 110, h: 110, fills: solid('#C94343')},
    '9:7': {type: 'RECT', parent: '9:1', idx: 'a5', name: 'Box', x: 440, y: 40, w: 80, h: 60, fills: solid('#1A1A1F')}
  });
  return doc;
}
/* runs in the page: helpers on window.V */
function helpers() {
  const V = window.V = {};
  V.px = (sx, sy) => { HD.render.flush(); const c = HD.render.canvas, d = HD.render.dpr, p = c.getContext('2d').getImageData(Math.round(sx * d), Math.round(sy * d), 1, 1).data; return [p[0], p[1], p[2]]; };
  V.wpx = (wx, wy) => { const s = HD.render.worldToScreen(wx, wy); return V.px(s[0], s[1]); };
  V.box = (id) => { const n = HD.store.get(id); return [n.x || 0, n.y || 0, HD.store.prop(id, 'w'), HD.store.prop(id, 'h')].map(v => Math.round(v * 100) / 100); };
  V.shot = (id, scale) => { const cv = HD.render.toCanvas(id, scale || 1, {bg: '#FFFFFF'}); return {w: cv.width, h: cv.height, d: cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data}; };
  V.diff = (a, b) => { if (a.w !== b.w || a.h !== b.h) return -1; let n = 0; for (let i = 0; i < a.d.length; i += 4) if (Math.max(Math.abs(a.d[i] - b.d[i]), Math.abs(a.d[i + 1] - b.d[i + 1]), Math.abs(a.d[i + 2] - b.d[i + 2])) > 40) n++; return n; };
  V.undoCount = () => { let n = 0; while (HD.store.canUndo() && n < 500) { HD.store.undo(); n++; } for (let i = 0; i < n; i++) HD.store.redo(); return n; };
  V.count = (rgb, tol) => { HD.render.flush(); const c = HD.render.canvas, d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - rgb[0]) <= tol && Math.abs(d[i + 1] - rgb[1]) <= tol && Math.abs(d[i + 2] - rgb[2]) <= tol) n++; return n; };
}
const near = (a, b, tol) => a.every((v, i) => Math.abs(v - b[i]) <= (tol === undefined ? 12 : tol));
const isColor = (got, want, msg, tol) => assert.ok(near(got, want, tol), msg + ': got rgb(' + got + ') want rgb(' + want + ')');

async function main() {
  let chromium;
  try { ({chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright')); } catch (e) { console.log('SKIP: playwright is not installed'); process.exit(77); }
  const shots = process.env.DESIGN_SHOTS || ''; if (shots) fs.mkdirSync(shots, {recursive: true});
  let browser;
  try { browser = await chromium.launch({executablePath: process.env.CHROMIUM_EXECUTABLE || undefined, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']}); }
  catch (e) { console.log('SKIP: Chromium can not start here: ' + String(e.message).split('\n')[0]); process.exit(77); }
  const mock = await startMock(seed());
  const errors = [], report = {checks: 0};
  const ok = (name) => { report.checks++; if (process.env.DESIGN_VERBOSE) console.log('ok ' + name); };
  async function open(viewport, scheme) {
    const page = await browser.newPage({viewport: viewport, colorScheme: scheme || 'light'});
    page.on('pageerror', e => errors.push(e.message + ' ' + String(e.stack || '').split('\n').slice(1, 3).join(' ')));
    page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|net::ERR/.test(m.text())) errors.push('console: ' + m.text()); });
    await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, r => r.fulfill({contentType: 'text/css', body: ''}));
    await page.addInitScript(() => { localStorage.setItem('hoola.console.token', 'fixture-only'); localStorage.removeItem('hoola.design.rulers'); localStorage.removeItem('hoola.design.grids'); });
    await page.goto('http://127.0.0.1:' + mock.port + '/console/design#/f/f1');
    await page.waitForFunction(() => window.HD && HD.ui && HD.ui.mounted && HD.net.status === 'live' && HD.store.pages().length > 0 && HD.vector, null, {timeout: 20000});
    await page.evaluate(helpers);
    await page.evaluate(() => new Promise(done => { let last = '', same = 0, n = 0; const tick = () => { const v = [HD.render.view.x, HD.render.view.y, HD.render.view.zoom].join(); same = v === last ? same + 1 : 0; last = v; if (same >= 3 || ++n > 90) setTimeout(done, 30); else requestAnimationFrame(tick); }; requestAnimationFrame(tick); }));
    return page;
  }
  const shot = async (page, name) => { if (shots) await page.screenshot({path: path.join(shots, name + '.png')}); };
  try {
    const page = await open({width: 1440, height: 900});
    const ev = (fn, arg) => page.evaluate(fn, arg);
    const origin = async () => ev(() => { const r = HD.tools.canvas.getBoundingClientRect(); return [r.left, r.top]; });
    const pt = async (wx, wy) => ev(([x, y]) => { const s = HD.render.worldToScreen(x, y), r = HD.tools.canvas.getBoundingClientRect(); return [r.left + s[0], r.top + s[1]]; }, [wx, wy]);
    const drag = async (a, b, opts) => { await page.mouse.move(a[0], a[1]); await page.mouse.down(); await page.mouse.move((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, {steps: 3}); await page.mouse.move(b[0], b[1], {steps: 3}); if (!(opts && opts.hold)) await page.mouse.up(); };
    const O = await origin();
    const canvasFocus = () => page.locator('.hd-canvas').focus();

    /* ---- the path parser: every command, relative forms, numbers without separators, arc flags written together ---- */
    const parse = await ev(() => {
      const G = HD.render.geom, r = (segs) => segs.map(s => [s[0]].concat(s.slice(1).map(v => Math.round(v * 100) / 100 + 0)));
      const bb = (d) => { const b = G.pathBBox(d); return [b.x0, b.y0, b.x1, b.y1].map(v => Math.round(v * 100) / 100 + 0); };
      return {
        rel: r(G.parsePath('m10 10 l20 0 0 20 h-20 v-10 z')), tight: r(G.parsePath('M1.5.5-2-3L1e1,2E0')), implicit: r(G.parsePath('M0 0 10 0 10 10')),
        smooth: r(G.parsePath('M0 0 C0 10 10 10 10 0 S20 -10 20 0')), quad: r(G.parsePath('M0 0 Q10 20 20 0 T40 0')),
        arcBox: bb('M0 50 A50 50 0 0 1 100 50 A50 50 0 0 1 0 50 Z'), arcFlags: bb('M0 50a50 50 0 01100 0a50 50 0 01-100 0z'), arcLarge: bb('M0 0 a10 10 0 1 0 20 0'),
        bad: r(G.parsePath('M0 0 L10 10 X 5 5 L20 20')), half: r(G.parsePath('M0 0 L10')), empty: G.parsePath('').length + G.parsePath(null).length + G.parsePath('hello').length,
        round: G.segsToD(G.parsePath('M0 0l10 0c0 5 5 10 10 10z')),
        model: (function () { const d = 'M0 50C0 20 30 0 60 0C90 0 120 20 120 50L120 100L0 100Z', m = HD.vector.model.toModel(G.parsePath(d)); return [m.length, m[0].pts.length, m[0].closed, m[0].pts[1].sm, m[0].pts[3].sm, HD.vector.model.toD(m)]; })(),
        two: (function () { const m = HD.vector.model.toModel(G.parsePath('M0 0L10 0L10 10M20 20C20 30 30 30 30 20Z')); return [m.length, m[0].closed, m[1].closed, m[1].pts.length]; })()
      };
    });
    assert.deepEqual(parse.rel, [['M', 10, 10], ['L', 30, 10], ['L', 30, 30], ['L', 10, 30], ['L', 10, 20], ['Z']]);
    assert.deepEqual(parse.tight, [['M', 1.5, 0.5], ['L', -2, -3], ['L', 10, 2]], 'numbers that run into each other, exponents');
    assert.deepEqual(parse.implicit, [['M', 0, 0], ['L', 10, 0], ['L', 10, 10]]);
    assert.deepEqual(parse.smooth[2], ['C', 10, -10, 20, -10, 20, 0], 'S mirrors the last handle');
    assert.deepEqual(parse.quad[2], ['C', 26.67, -13.33, 33.33, -13.33, 40, 0], 'T mirrors the last quadratic handle');
    assert.deepEqual(parse.arcBox, [0, 0, 100, 100]); assert.deepEqual(parse.arcFlags, [0, 0, 100, 100], 'arc flags without separators'); assert.deepEqual(parse.arcLarge, [0, 0, 20, 10]);
    assert.deepEqual(parse.bad, [['M', 0, 0], ['L', 10, 10]], 'what came before a bad command stays'); assert.deepEqual(parse.half, [['M', 0, 0]]); assert.equal(parse.empty, 0);
    assert.equal(parse.round, 'M0 0L10 0C10 5 15 10 20 10Z');
    assert.deepEqual(parse.model, [1, 5, true, true, false, 'M0 50C0 20 30 0 60 0C90 0 120 20 120 50L120 100L0 100Z'], 'path -> points -> the same path');
    assert.deepEqual(parse.two, [2, false, true, 2]);
    ok('path parser');

    /* ---- vector edit mode ---- */
    await canvasFocus();
    let p = await pt(100, 110);
    await page.mouse.click(p[0], p[1]); await page.mouse.dblclick(p[0], p[1]);
    assert.deepEqual(await ev(() => [HD.vector.editing, HD.tools.current]), ['9:2', 'vedit'], 'a double click on a vector opens its points');
    await page.locator('.hdv-bar').waitFor();
    let dbg = await ev(() => HD.vector.debug());
    assert.equal(dbg.subs[0].pts.length, 5);
    const undo0 = await ev(() => V.undoCount());
    /* drag the top point 30 up: the box grows upward, every other point stays where it is on the screen */
    const top = dbg.subs[0].pts[1].s;
    await drag([O[0] + top[0], O[1] + top[1]], [O[0] + top[0], O[1] + top[1] - 30]);
    assert.deepEqual(await ev(() => V.box('9:2')), [40, 10, 120, 130], 'the box hugs the edited path');
    assert.equal(await ev(() => HD.store.get('9:2').path), 'M0 80C0 50 30 0 60 0C90 0 120 50 120 80L120 130L0 130Z');
    let d2 = await ev(() => HD.vector.debug());
    for (const i of [0, 2, 3, 4]) assert.ok(Math.abs(d2.subs[0].pts[i].s[0] - dbg.subs[0].pts[i].s[0]) < 0.6 && Math.abs(d2.subs[0].pts[i].s[1] - dbg.subs[0].pts[i].s[1]) < 0.6, 'point ' + i + ' did not move');
    assert.ok(Math.abs(d2.subs[0].pts[1].s[1] - (top[1] - 30)) < 1, 'the dragged point followed the pointer');
    assert.equal(await ev(() => V.undoCount()), undo0 + 1, 'a whole drag is one undo step');
    isColor(await ev(() => V.wpx(100, 30)), [110, 85, 240], 'the shape is painted where the point went', 16);
    /* a click on a straight side adds a point; dragging it moves only it */
    let q = await pt(100, 140);
    await page.mouse.click(q[0], q[1]);
    assert.equal(await ev(() => HD.vector.debug().subs[0].pts.length), 6, 'a click on a line adds a point');
    assert.deepEqual(await ev(() => HD.vector.debug().sel), ['0/4'], 'and selects it');
    await drag(q, [q[0], q[1] + 20]);
    assert.deepEqual(await ev(() => V.box('9:2')), [40, 10, 120, 150]);
    /* double click a corner point: smooth; again: corner */
    await page.mouse.dblclick(q[0], q[1] + 20);
    assert.ok(await ev(() => { const p0 = HD.vector.debug().subs[0].pts[4]; return !!(p0.i && p0.o && p0.sm); }), 'a double click makes a point smooth');
    assert.equal(await page.locator('.hdv-bar button', {hasText: 'Corner'}).count(), 1);
    await page.locator('.hdv-bar button', {hasText: 'Corner'}).click();
    assert.ok(await ev(() => { const p0 = HD.vector.debug().subs[0].pts[4]; return !p0.i && !p0.o; }), 'the bar turns it back into a corner');
    /* drag a handle of a smooth point: the other handle stays in line */
    await page.mouse.click(O[0] + top[0], O[1] + top[1] - 30);
    let tp = await ev(() => HD.vector.debug().subs[0].pts[1]);
    await drag([O[0] + tp.o[0], O[1] + tp.o[1]], [O[0] + tp.o[0] + 10, O[1] + tp.o[1] + 20]);
    tp = await ev(() => HD.vector.debug().subs[0].pts[1]);
    const cross = (tp.o[0] - tp.s[0]) * (tp.i[1] - tp.s[1]) - (tp.o[1] - tp.s[1]) * (tp.i[0] - tp.s[0]);
    assert.ok(Math.abs(cross) < 40 && (tp.o[0] - tp.s[0]) * (tp.i[0] - tp.s[0]) < 0, 'the two handles of a smooth point stay in one line: ' + JSON.stringify(tp));
    /* bend the straight right side by dragging it */
    const before = await ev(() => HD.store.get('9:2').path);
    q = await pt(160, 125); await drag(q, [q[0] + 24, q[1]]);
    const bent = await ev(() => { const n = HD.store.get('9:2'); return [n.path, n.w]; });
    assert.ok(bent[0] !== before && bent[1] > 135 && bent[1] < 150, 'dragging a side bends it and the box follows: ' + bent[1]);
    await shot(page, 'vector-edit');
    assert.deepEqual(await ev(layoutProblems), [], 'layout with the edit bar');
    /* open / close the path, delete a point with the keyboard (the layer itself stays) */
    await page.locator('.hdv-bar button', {hasText: 'Open path'}).click();
    assert.ok(!/Z/.test(await ev(() => HD.store.get('9:2').path)), 'Open path');
    await page.locator('.hdv-bar button', {hasText: 'Close path'}).click();
    assert.ok(/Z$/.test(await ev(() => HD.store.get('9:2').path)), 'Close path');
    await canvasFocus();
    await page.mouse.click(O[0] + top[0], O[1] + top[1] - 30); await page.keyboard.press('Delete');
    assert.deepEqual(await ev(() => [HD.store.has('9:2'), HD.vector.debug().subs[0].pts.length]), [true, 5], 'Delete removes the point, not the layer');
    await page.keyboard.press('Control+a'); assert.equal(await ev(() => HD.vector.debug().sel.length), 5, 'Ctrl+A chooses every point');
    await page.keyboard.press('ArrowRight'); assert.equal(await ev(() => V.box('9:2')[0]), 41, 'arrow keys nudge the chosen points');
    /* undo all the way inside the mode: the mode follows the document */
    await ev(() => { for (let i = 0; i < 40 && HD.store.canUndo(); i++) HD.store.undo(); });
    assert.deepEqual(await ev(() => [HD.store.get('9:2').path, V.box('9:2'), HD.vector.editing]), ['M0 50C0 20 30 0 60 0C90 0 120 20 120 50L120 100L0 100Z', [40, 40, 120, 100], '9:2']);
    await page.keyboard.press('Escape'); await page.keyboard.press('Escape');
    assert.deepEqual(await ev(() => [HD.vector.editing, HD.tools.current]), [null, 'move'], 'Escape leaves the mode');
    assert.equal(await page.locator('.hdv-bar').count(), 0);
    ok('vector edit');

    /* ---- Edit shape: a rounded rectangle becomes a vector that looks the same; Enter opens a vector ---- */
    const conv = await ev(() => { const a = V.shot('9:3', 2); HD.sel.set(['9:3']); const r = HD.vector.editShape(); const n = HD.store.get('9:3'); const b = V.shot('9:3', 2); return [r, n.type, n.radius === undefined, V.diff(a, b), HD.vector.editing, V.box('9:3')]; });
    assert.deepEqual(conv.slice(0, 3), [true, 'VECTOR', true]); assert.ok(conv[3] >= 0 && conv[3] < 12, 'the vector looks like the rectangle it was: ' + conv[3] + ' pixels differ'); assert.equal(conv[4], '9:3'); assert.deepEqual(conv[5], [220, 40, 120, 100]);
    await page.keyboard.press('Enter'); assert.equal(await ev(() => HD.vector.editing), null);
    await ev(() => HD.store.undo()); assert.equal(await ev(() => HD.store.get('9:3').type), 'RECT', 'one undo brings the rectangle back');
    await ev(() => HD.sel.set(['9:2'])); await canvasFocus(); await page.keyboard.press('Enter'); assert.equal(await ev(() => HD.vector.editing), '9:2', 'Enter on a vector opens its points'); await page.keyboard.press('Enter');
    ok('edit shape');

    /* ---- boolean groups: the geometry against a compositing reference, for all four ---- */
    const bools = await ev(() => {
      const G = HD.render.geom, st = HD.store, out = {};
      HD.sel.set(['9:3', '9:4']);
      const gid = HD.vector.bool('union'); out.gid = gid; out.node = JSON.parse(JSON.stringify(st.get(gid))); out.kids = st.children(gid).slice();
      const ref = (op) => {      /* the two outlines combined with canvas compositing: what the result must cover */
        const c = document.createElement('canvas'); c.width = 400; c.height = 360; const x = c.getContext('2d'); x.scale(2, 2);
        const kids = st.children(gid).map(id => { const n = st.get(id), o = G.outlineSegs(n, n.type, n.w, n.h), p = new Path2D(); p.addPath(new Path2D(G.segsToD(o.segs)), new DOMMatrix([1, 0, 0, 1, n.x, n.y])); return p; });
        x.fillStyle = '#000';
        if (op === 'union') { for (const k of kids) x.fill(k); }
        else if (op === 'subtract') { x.fill(kids[0]); x.globalCompositeOperation = 'destination-out'; x.fill(kids[1]); }
        else if (op === 'intersect') { x.save(); x.clip(kids[1]); x.fill(kids[0]); x.restore(); }
        else { const all = new Path2D(); for (const k of kids) all.addPath(k); x.fill(all, 'evenodd'); }
        return x.getImageData(0, 0, 400, 360).data;
      };
      const mine = (d) => { const c = document.createElement('canvas'); c.width = 400; c.height = 360; const x = c.getContext('2d'); x.scale(2, 2); x.fillStyle = '#000'; x.fill(new Path2D(d)); return x.getImageData(0, 0, 400, 360).data; };
      out.ops = {};
      for (const op of ['union', 'subtract', 'intersect', 'exclude']) {
        HD.vector.bool(op);
        const b = G.boolPath(gid), a = ref(op), m = mine(b.d);
        let bad = 0, area = 0;
        for (let i = 3; i < a.length; i += 4) { if (a[i] > 128) area++; if (Math.abs(a[i] - m[i]) > 128) bad++; }
        out.ops[op] = {bad, area, curves: (b.d.match(/C/g) || []).length, loops: (b.d.match(/M/g) || []).length, len: b.d.length, bool: st.get(gid).bool, name: st.get(gid).name};
      }
      return out;
    });
    assert.equal(bools.node.type, 'GROUP'); assert.equal(bools.node.bool, 'union'); assert.equal(bools.node.name, 'Union'); assert.deepEqual(bools.kids, ['9:3', '9:4']);
    assert.deepEqual(bools.node.fills, solid('#EE8F35'), 'the result takes the fill of the bottom shape');
    for (const op of ['union', 'subtract', 'intersect', 'exclude']) { const r = bools.ops[op];
      assert.ok(r.area > 3000 && r.bad < r.area * 0.004 + 40, op + ': the outline matches the composited shapes (' + r.bad + ' of ' + r.area + ' pixels differ)');
      assert.ok(r.curves >= 2 && r.len < 900, op + ': the result is curves, not a polygon of hundreds of points (' + r.len + ' chars)'); assert.equal(r.bool, op); }
    assert.ok(bools.ops.exclude.loops >= 1 && bools.ops.subtract.loops === 1); assert.equal(bools.ops.exclude.name, 'Exclude');
    report.bool = bools.ops;
    /* on the canvas: subtract, a stroke and a shadow style the RESULT */
    const gid = bools.gid;
    const sub = await ev((g) => {
      HD.vector.bool('subtract');
      HD.store.tx('style', () => HD.store.set(g, {strokes: [{type: 'solid', color: '#0000FF', opacity: 1, visible: true}], strokeWeight: 6, strokeAlign: 'center'}));
      const o = {keep: V.wpx(240, 60), cut: V.wpx(345, 145), edge: V.wpx(290 + 55 - 55 * Math.SQRT1_2, 90 + 55 - 55 * Math.SQRT1_2), inner: V.wpx(330, 80), rightEdge: V.wpx(340, 60)};
      o.hitKeep = HD.render.hitTest(240, 60, {deep: false}); o.hitDeep = HD.render.hitTest(240, 60, {deep: true}); o.hitCut = HD.render.hitTest(360, 160, {deep: true});
      const svg = HD.render.toSVG(g); o.svgPaths = (svg.match(/<path /g) || []).length; o.svgHasEllipse = /<ellipse/.test(svg); o.svgStroke = /stroke="#0000FF"/i.test(svg);
      return o;
    }, gid);
    isColor(sub.keep, [238, 143, 53], 'the kept part has the fill'); isColor(sub.cut, [255, 255, 255], 'the cut-away part is gone'); isColor(sub.edge, [0, 0, 255], 'the cut edge carries the stroke of the result', 60);
    isColor(sub.inner, [238, 143, 53], 'no stroke of a part runs through the result'); isColor(sub.rightEdge, [0, 0, 255], 'the outer edge is stroked', 60);
    assert.equal(sub.hitKeep, gid); assert.equal(sub.hitDeep, '9:3', 'a deep hit offers the part under the pointer'); assert.notEqual(sub.hitCut, gid, 'the cut-away area is not the group');
    assert.ok(sub.svgPaths >= 2 && !sub.svgHasEllipse && sub.svgStroke, 'SVG: one path for the result, not the parts');
    await ev((g) => HD.sel.set([g]), gid); await page.waitForTimeout(80);
    assert.ok(await page.locator('.hd-lrow.bool').count() >= 1, 'the layers list marks the boolean group');
    assert.equal(await page.locator('section[aria-label="Fill"]').count(), 1, 'a boolean group has its own Fill section');
    assert.equal(await page.locator('section[aria-label="Boolean"] select').inputValue(), 'subtract');
    await page.locator('section[aria-label="Boolean"] select').selectOption('intersect');
    assert.equal(await ev((g) => HD.store.get(g).bool, gid), 'intersect', 'the panel changes the way of combining');
    await shot(page, 'boolean-intersect');
    assert.deepEqual(await ev(layoutProblems), [], 'layout with a boolean group selected');
    /* flatten: one vector that looks the same; one undo brings the group back */
    const flat = await ev((g) => { HD.vector.bool('exclude'); HD.store.tx('s', () => HD.store.set(g, {strokes: []})); const a = V.shot('9:1', 2), u = V.undoCount(); HD.sel.set([g]); const out = HD.vector.flatten(), n = HD.store.get(out), b = V.shot('9:1', 2);
      const r = {type: n.type, gone: !HD.store.has(g), kidsGone: !HD.store.has('9:3'), diff: V.diff(a, b), steps: V.undoCount() - u, box: V.box(out), sel: HD.sel.ids.slice(), fills: n.fills};
      HD.store.undo(); r.back = HD.store.has(g) && HD.store.has('9:3') && !HD.store.has(out); HD.store.redo(); r.out = out; return r; }, gid);
    assert.deepEqual([flat.type, flat.gone, flat.kidsGone, flat.steps, flat.back], ['VECTOR', true, true, 1, true]); assert.ok(flat.diff >= 0 && flat.diff < 40, 'the flattened vector looks like the group: ' + flat.diff + ' pixels differ');
    assert.deepEqual(flat.box, [220, 40, 180, 160]); assert.deepEqual(flat.sel, [flat.out]); assert.deepEqual(flat.fills, solid('#EE8F35'));
    /* flatten two loose shapes = their union; text refuses, plainly */
    const loose = await ev(() => { HD.sel.set(['9:6', '9:7']); const out = HD.vector.flatten(); const n = HD.store.get(out); const r = [n.type, V.box(out), (n.path.match(/M/g) || []).length]; HD.store.undo(); return r; });
    assert.deepEqual(loose, ['VECTOR', [440, 40, 110, 300], 2], 'two shapes that do not touch flatten into one vector with two pieces');
    ok('booleans + flatten');

    /* ---- masks ---- */
    const mk = await ev(() => {
      const st = HD.store, o = {};
      st.tx('m', () => { o.m = st.create('ELLIPSE', '9:1', {name: 'Mask', x: 60, y: 230, w: 100, h: 100, fills: [{type: 'solid', color: '#000000', opacity: 1, visible: true}]}, '9:5'); });
      HD.sel.set([o.m]); HD.vector.mask();
      o.on = st.get(o.m).mask; o.inside = V.wpx(150, 280); o.tint = V.wpx(110, 280); o.outside = V.wpx(240, 240);
      /* a see-through mask shows less; a mask stops at the next mask */
      st.tx('a', () => st.set(o.m, {fills: [{type: 'solid', color: '#000000', opacity: 0.5, visible: true}]})); o.half = V.wpx(110, 280);
      st.tx('a', () => st.set(o.m, {fills: [{type: 'solid', color: '#000000', opacity: 1, visible: true}]}));
      HD.sel.set([o.m]); HD.vector.mask(); o.off = st.get(o.m).mask === undefined; o.after = V.wpx(240, 240);
      st.tx('a', () => st.set(o.m, {mask: true}));
      return o;
    });
    assert.equal(mk.on, true); isColor(mk.inside, [255, 255, 255], 'inside the mask the layer above shows (the white middle of the gradient)', 20); isColor(mk.outside, [255, 255, 255], 'outside the mask it is cut away');
    assert.ok(mk.tint[0] > 140 && mk.tint[0] < 185 && mk.tint[2] > 240, 'the gradient shows through the mask: ' + mk.tint); assert.ok(mk.half[0] > mk.tint[0] + 30 && mk.half[0] < 230 && mk.half[2] > 240, 'a 50% see-through mask shows half as much: ' + mk.half + ' vs ' + mk.tint); assert.equal(mk.off, true, 'Use as mask again removes it'); assert.ok(mk.after[2] > 200 && mk.after[0] < 120, 'without the mask the gradient is whole again: ' + mk.after);
    await ev(() => HD.sel.clear()); await page.waitForTimeout(80);
    assert.equal(await page.locator('.hd-lrow.mask').count(), 1, 'the layers list marks the mask');
    await ev((m) => HD.store.tx('rm', () => HD.store.remove([m])), mk.m);
    ok('masks');

    /* ---- rulers + guides ---- */
    await canvasFocus();
    const bare = await ev(() => V.px(300, 8));
    await page.keyboard.press('Shift+R');
    assert.equal(await ev(() => HD.vector.rulers), true, 'Shift+R shows the rulers');
    assert.notDeepEqual(await ev(() => V.px(300, 8)), bare, 'the ruler is drawn');
    const u1 = await ev(() => V.undoCount());
    p = await pt(100, 100); await drag([O[0] + 8, O[1] + 300], p);
    p = await pt(300, 200); await drag([O[0] + 300, O[1] + 8], p);
    assert.deepEqual(await ev(() => HD.store.get(HD.sel.page).guides), [{axis: 'x', pos: 100}, {axis: 'y', pos: 200}], 'guides pulled out of the rulers are kept on the page');
    assert.equal(await ev(() => V.undoCount()), u1 + 2, 'one undo step a guide');
    assert.ok(mock.files.get('f1').doc.nodes['0:1'].guides.length === 2, 'the guides reached the server');
    /* a layer dragged near a guide snaps to it */
    p = await pt(480, 70); const p3 = await pt(480 - 337, 70 + 3);
    await drag(p, p3);
    assert.equal(await ev(() => V.box('9:7')[0]), 100, 'the left edge snapped to the guide at 100: ' + JSON.stringify(await ev(() => V.box('9:7'))));
    await shot(page, 'rulers-guides');
    /* move a guide, then drag it back onto the ruler: gone */
    await ev(() => HD.sel.clear());
    p = await pt(100, 380); const p4 = await pt(160, 380); await drag(p, p4);
    assert.deepEqual(await ev(() => HD.store.get(HD.sel.page).guides[0]), {axis: 'x', pos: 160});
    await drag(p4, [O[0] + 6, p4[1]]);
    assert.deepEqual(await ev(() => HD.store.get(HD.sel.page).guides), [{axis: 'y', pos: 200}], 'a guide dragged back onto its ruler is removed');
    assert.deepEqual(await ev(layoutProblems), [], 'layout with rulers');
    await page.keyboard.press('Shift+R'); assert.equal(await ev(() => HD.vector.rulers), false);
    ok('rulers + guides');

    /* ---- layout grids ---- */
    await ev(() => HD.sel.set(['9:1'])); await page.waitForTimeout(120);
    const plain = await ev(() => V.wpx(590, 390));
    const addGrid = page.locator('section[aria-label="Layout grid"] button[title="Add a layout grid"]');
    await addGrid.scrollIntoViewIfNeeded(); await addGrid.click(); await page.waitForTimeout(80);
    await page.locator('section[aria-label="Layout grid"] button[title="Add a layout grid"]').click(); await page.waitForTimeout(80);
    const grids = await ev(() => HD.store.get('9:1').grids);
    assert.deepEqual(grids.map(g => g.type), ['grid', 'columns'], 'the panel adds a grid, then columns');
    await page.locator('section[aria-label="Layout grid"] .hdv-grid').nth(1).locator('input').fill('3'); await page.keyboard.press('Enter');
    assert.equal(await ev(() => HD.store.get('9:1').grids[1].count), 3);
    const tint = await ev(() => V.wpx(590, 390));
    assert.ok(tint[0] > tint[1] + 10 && tint[1] < 245, 'a column tints the frame red: ' + tint + ' (was ' + plain + ')');
    isColor(await ev(() => V.wpx(198, 395)), plain, 'the gutter between two columns is clear', 30);
    const exp = await ev(() => { const s = V.shot('9:1', 1), i = (390 * s.w + 590) * 4; return [s.d[i], s.d[i + 1], s.d[i + 2]]; });
    isColor(exp, [255, 255, 255], 'a layout grid is never part of an export', 2);
    await page.locator('section[aria-label="Layout grid"] button[title="Layout grid settings"]').last().click(); await page.locator('.hdv-pop').waitFor();
    /* the Design panel is scrolled down to the grid section here: rows scrolled out above it are not a fault */
    assert.deepEqual((await ev(layoutProblems)).filter(x => !/^outside the window: /.test(x)), [], 'layout with the grid settings open');
    await shot(page, 'layout-grid');
    await page.keyboard.press('Escape'); await canvasFocus();
    await page.keyboard.press('Shift+G'); isColor(await ev(() => V.wpx(590, 390)), plain, 'Shift+G hides the layout grids', 2);
    await page.keyboard.press('Shift+G'); assert.equal(await ev(() => HD.vector.grids), true);
    await ev(() => HD.store.tx('g', () => HD.store.set('9:1', {grids: null})));
    ok('layout grids');

    /* ---- gradient handles on the canvas + the elliptical radial gradient ---- */
    const rad = await ev(() => [V.wpx(150, 280), V.wpx(150, 224), V.wpx(256, 280), V.wpx(44, 224)]);
    isColor(rad[0], [255, 255, 255], 'radial: white in the middle', 16);
    assert.ok(rad[1][0] < 80 && rad[1][2] > 200, 'radial in a wide box is an ellipse: the top middle is the end colour, ' + rad[1]);
    assert.ok(rad[2][0] < 60 && rad[2][2] > 200, 'and so is the right middle: ' + rad[2]);
    const u2 = await ev(() => V.undoCount());
    await ev(() => HD.sel.set(['9:5'])); await page.waitForTimeout(120);
    const sw = page.locator('section[aria-label="Fill"] .hd-sw.big').first(); await sw.scrollIntoViewIfNeeded(); await sw.click(); await page.locator('.hd-picker').waitFor();
    const gh = await ev(() => HD.vector.gradientHandles());
    const c0 = await pt(150, 280), c1 = await pt(260, 280);
    assert.ok(Math.abs(O[0] + gh.from[0] - c0[0]) < 1 && Math.abs(O[0] + gh.to[0] - c1[0]) < 1 && gh.stops.length === 2, 'the handles sit on the start and the end of the gradient: ' + JSON.stringify(gh));
    await drag([O[0] + gh.to[0], O[1] + gh.to[1]], [O[0] + gh.to[0] - 55, O[1] + gh.to[1] + 30]);
    const pnt = await ev(() => HD.store.get('9:5').fills[0]);
    assert.deepEqual(pnt.to, [0.75, 0.75], 'dragging the end handle moves the end of the gradient'); assert.deepEqual(pnt.from, [0.5, 0.5]);
    assert.equal(await page.locator('.hd-picker').count(), 1, 'the colour picker stays open while a handle is dragged');
    await shot(page, 'gradient-handles');
    await page.keyboard.press('Escape'); assert.equal(await ev(() => HD.vector.gradientHandles()), null, 'no handles once the picker is closed');
    assert.equal(await ev(() => V.undoCount()), u2 + 1, 'the whole handle drag is one undo step');
    ok('gradient handles');

    /* ---- distances while Alt is held ---- */
    await ev(() => HD.sel.set(['9:6'])); await canvasFocus();
    const red0 = await ev(() => V.count([229, 72, 77], 3));
    p = await pt(150, 280); await page.mouse.move(p[0], p[1]); await page.keyboard.down('Alt'); await page.mouse.move(p[0] + 2, p[1] + 1); await page.waitForTimeout(60);
    const red1 = await ev(() => V.count([229, 72, 77], 3));
    await shot(page, 'distances');
    await page.keyboard.up('Alt'); await page.mouse.move(p[0] + 4, p[1] + 2); await page.waitForTimeout(60);
    assert.ok(red1 > red0 + 400, 'Alt over another layer draws the red distance lines (' + red0 + ' -> ' + red1 + ' red pixels)'); assert.ok(await ev(() => V.count([229, 72, 77], 3)) <= red0 + 5, 'and they go when Alt is let go');
    ok('distances');

    /* ---- renderer + layout fixes ---- */
    const fx = await ev(() => {
      const st = HD.store, pg = HD.sel.page, o = {}, solid = (c, op) => [{type: 'solid', color: c, opacity: op === undefined ? 1 : op, visible: true}];
      st.tx('g', () => {
        st.remove(st.children(pg));
        const F = st.create('FRAME', pg, {name: 'Fixes', x: 0, y: 0, w: 900, h: 520, fills: solid('#FFFFFF')}); o.F = F;
        o.tFill = st.create('TEXT', F, {x: 20, y: 10, chars: 'HIH', fontSize: 80, fontWeight: 700, fills: solid('#FFD34D')});
        o.tIn = st.create('TEXT', F, {x: 20, y: 110, chars: 'HIH', fontSize: 80, fontWeight: 700, fills: solid('#FFD34D'), strokes: solid('#0000FF'), strokeWeight: 3, strokeAlign: 'inside'});
        o.tOut = st.create('TEXT', F, {x: 20, y: 210, chars: 'HIH', fontSize: 80, fontWeight: 700, fills: solid('#FFD34D'), strokes: solid('#0000FF'), strokeWeight: 3, strokeAlign: 'outside'});
        o.tSpread = st.create('TEXT', F, {x: 20, y: 310, chars: 'HIH', fontSize: 80, fontWeight: 700, fills: solid('#FFD34D'), effects: [{type: 'drop', x: 0, y: 0, blur: 0, spread: 5, color: '#FF0000', opacity: 1, visible: true}]});
        o.star = st.create('STAR', F, {x: 300, y: 20, w: 100, h: 100, fills: solid('#6E55F0'), effects: [{type: 'drop', x: 0, y: 0, blur: 0, spread: 8, color: '#FF0000', opacity: 1, visible: true}]});
        o.off = st.create('VECTOR', F, {x: 300, y: 160, w: 100, h: 80, path: 'M40 40 L90 40 L65 80 Z', fills: solid('#13875F')});
        const C = st.create('COMPONENT', F, {name: 'Btn', x: 460, y: 20, w: 160, h: 48, fills: solid('#5B45E0'), layout: {mode: 'h', gap: 8, pad: [12, 16, 12, 16], alignMain: 'between', alignCross: 'center'}});
        st.create('ELLIPSE', C, {w: 24, h: 24, fills: solid('#FFFFFF')}); st.create('RECT', C, {w: 24, h: 24, fills: solid('#00FF00')});
        o.inst = st.create('INSTANCE', F, {x: 460, y: 90, w: 320, h: 48, comp: C});
        const C2 = st.create('COMPONENT', F, {name: 'Card', x: 460, y: 160, w: 160, h: 100, fills: solid('#EEEBFD')});
        st.create('RECT', C2, {x: 120, y: 10, w: 30, h: 30, fills: solid('#FF0000'), cons: {h: 'right', v: 'top'}});
        st.create('RECT', C2, {x: 10, y: 70, w: 140, h: 20, fills: solid('#00AA00'), cons: {h: 'leftright', v: 'bottom'}});
        o.inst2 = st.create('INSTANCE', F, {x: 460, y: 280, w: 300, h: 160, comp: C2});
        const C3 = st.create('COMPONENT', F, {name: 'Plain', x: 640, y: 160, w: 80, h: 50, fills: solid('#FBF0DF')});
        st.create('RECT', C3, {x: 10, y: 10, w: 20, h: 20, fills: solid('#EE8F35')});
        o.inst3 = st.create('INSTANCE', F, {x: 780, y: 160, w: 80, h: 100, comp: C3});
        o.AL = st.create('FRAME', F, {name: 'AL', x: 300, y: 300, w: 100, h: 100, fills: solid('#F3F3F2'), sizeH: 'hug', sizeV: 'hug', layout: {mode: 'h', gap: 10, pad: [10, 10, 10, 10], alignCross: 'center'}});
        st.create('RECT', o.AL, {w: 40, h: 40, fills: solid('#5B45E0')}); o.turned = st.create('RECT', o.AL, {w: 80, h: 20, rot: 45, fills: solid('#EE8F35')}); o.last = st.create('RECT', o.AL, {w: 40, h: 40, fills: solid('#13875F')});
      });
      HD.sel.clear(); HD.render.setView({x: 20, y: 20, zoom: 1}); HD.render.flush();
      /* one read of the whole canvas; world (x, y) -> its pixel */
      const cvs = HD.render.canvas, dpr = HD.render.dpr, img = cvs.getContext('2d').getImageData(0, 0, cvs.width, cvs.height), at = (wx, wy) => { const sp = HD.render.worldToScreen(wx, wy), i = (Math.round(sp[1] * dpr) * img.width + Math.round(sp[0] * dpr)) * 4; return [img.data[i], img.data[i + 1], img.data[i + 2]]; };
      const ink = (id, pad, test) => { const b = st.worldBounds(id); let x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1; for (let y = Math.floor(b.y) - pad; y < b.y + b.h + pad; y++) for (let x = Math.floor(b.x) - pad; x < b.x + b.w + pad; x++) { if (test(at(x, y))) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; } } return [x0 - b.x, y0 - b.y, x1 - b.x, y1 - b.y].map(v => Math.round(v)); };
      const notWhite = (q) => q[0] + q[1] + q[2] < 700, blue = (q) => q[2] > 180 && q[0] < 90, yellow = (q) => q[0] > 220 && q[1] > 170 && q[2] < 140, red = (q) => q[0] > 200 && q[1] < 70 && q[2] < 70;
      o.fill = ink(o.tFill, 8, notWhite); o.inAll = ink(o.tIn, 8, notWhite); o.inBlue = ink(o.tIn, 8, blue); o.inYellow = ink(o.tIn, 8, yellow); o.outAll = ink(o.tOut, 8, notWhite); o.outYellow = ink(o.tOut, 8, yellow); o.spreadRed = ink(o.tSpread, 10, red);
      o.starRed = ink(o.star, 12, red); o.offInk = ink(o.off, 4, notWhite);
      o.inst = [V.wpx(460 + 28, 114), V.wpx(460 + 320 - 28, 114), V.wpx(460 + 160, 114)];
      o.inst2 = [V.wpx(460 + 300 - 25, 280 + 25), V.wpx(460 + 135, 280 + 25), V.wpx(460 + 280, 280 + 140), V.wpx(460 + 20, 280 + 140), V.wpx(460 + 80, 280 + 80)];
      o.inst3 = [V.wpx(780 + 20, 160 + 40), V.wpx(780 + 20, 160 + 15)];
      o.alBox = V.box(o.AL); o.turnedBox = V.box(o.turned); o.lastBox = V.box(o.last);
      const svg = HD.render.toSVG(o.F); o.svg = {radialT: /gradientTransform="scale\(/.test(svg), clipText: /<clipPath[^>]*><text/.test(svg), erode: svg.length};
      return o;
    });
    assert.ok(fx.inAll.every((v, i) => Math.abs(v - fx.fill[i]) <= 1), 'a stroke INSIDE the letters adds no ink outside them: ' + fx.inAll + ' vs ' + fx.fill);
    assert.ok(fx.inBlue[0] <= fx.fill[0] + 1 && fx.inBlue[2] >= fx.fill[2] - 1 && fx.inYellow[0] >= fx.fill[0] + 2, 'the inside stroke runs along the edge, the fill is inside it: blue ' + fx.inBlue + ' yellow ' + fx.inYellow);
    assert.ok(fx.outAll[0] <= fx.fill[0] - 2 && fx.outAll[2] >= fx.fill[2] + 2 && fx.outAll[1] <= fx.fill[1] - 2, 'a stroke OUTSIDE widens the letters: ' + fx.outAll + ' vs ' + fx.fill);
    assert.ok(Math.abs(fx.outYellow[0] - fx.fill[0]) <= 1 && Math.abs(fx.outYellow[2] - fx.fill[2]) <= 1, 'and leaves the fill whole: ' + fx.outYellow);
    assert.ok(fx.spreadRed[0] <= fx.fill[0] - 3 && fx.spreadRed[0] >= fx.fill[0] - 7 && fx.spreadRed[2] >= fx.fill[2] + 3, 'shadow spread on text grows the shadow about 5 px: ' + fx.spreadRed + ' vs ' + fx.fill);
    assert.ok(fx.starRed[1] <= -6 && fx.starRed[1] >= -10 && fx.starRed[3] >= 102, 'shadow spread on a star: ' + fx.starRed);
    assert.ok(fx.offInk[0] <= 1 && fx.offInk[1] <= 1 && fx.offInk[2] >= 98 && fx.offInk[3] >= 78, 'a path that does not start at 0,0 fills its box: ' + fx.offInk);
    isColor(fx.inst[0], [255, 255, 255], 'instance of an auto layout component: the first child keeps its size at the left'); isColor(fx.inst[1], [0, 255, 0], 'the last child sits at the right end'); isColor(fx.inst[2], [91, 69, 224], 'nothing is stretched in between');
    isColor(fx.inst2[0], [255, 0, 0], 'constraints in an instance: pinned right + top'); isColor(fx.inst2[1], [238, 235, 253], 'not where plain scaling would put it'); isColor(fx.inst2[2], [0, 170, 0], 'left + right stretches, bottom follows'); isColor(fx.inst2[3], [0, 170, 0], 'from the left margin'); isColor(fx.inst2[4], [238, 235, 253], 'the bar keeps its height');
    isColor(fx.inst3[0], [238, 143, 53], 'a component without layout or constraints is still scaled'); isColor(fx.inst3[1], [251, 240, 223], 'scaled');
    assert.deepEqual(fx.alBox.slice(2), [190.71, 90.71], 'auto layout gives a turned child the room of its turned box'); assert.ok(near(fx.turnedBox, [55.36, 35.36, 80, 20], 0.02), 'the turned child is placed by its turned box: ' + fx.turnedBox); assert.ok(near(fx.lastBox.slice(0, 2), [140.71, 25.36], 0.02), 'and the next child comes after it: ' + fx.lastBox);
    assert.ok(fx.svg.clipText, 'SVG: the inside stroke of a text is cut by the letters');
    await shot(page, 'fixes');
    ok('renderer + layout fixes');
    await page.close();

    /* ---- dark: rulers, guides, the edit bar and the grid section look right and break no layout rule ---- */
    const dark = await open({width: 1280, height: 800}, 'dark');
    await dark.locator('.hd-canvas').focus(); await dark.keyboard.press('Shift+R');
    const dk = await dark.evaluate(() => {
      const st = HD.store, F = st.children(HD.sel.page)[0]; let v = null;
      HD.vector.setGuides([{axis: 'x', pos: 30}, {axis: 'y', pos: 150}]);
      st.tx('g', () => { st.set(F, {grids: [{type: 'columns', count: 4, gutter: 16, margin: 24, color: '#FF0000', opacity: 0.12, visible: true}]}); v = st.create('VECTOR', F, {name: 'Leaf', x: 620, y: 300, w: 160, h: 120, path: 'M0 120C0 40 60 0 160 0C160 80 100 120 0 120Z', fills: [{type: 'solid', color: '#3FCB98', opacity: 1, visible: true}]}); });
      HD.sel.set([F]); const r = V.px(300, 8); HD.sel.set([v]); HD.vector.edit(v); return {ruler: r, edit: HD.vector.editing === v, guides: st.get(HD.sel.page).guides.length};
    });
    assert.ok(dk.ruler[0] < 60 && dk.ruler[1] < 60, 'the ruler follows the dark theme: ' + dk.ruler); assert.equal(dk.edit, true); assert.equal(dk.guides, 2);
    await dark.locator('.hdv-bar.below').waitFor();
    assert.deepEqual(await dark.evaluate(layoutProblems), [], 'layout, dark, 1280 wide');
    if (shots) await dark.screenshot({path: path.join(shots, 'dark-rulers-edit.png')});
    await dark.close();
    ok('dark');

    assert.deepEqual(errors, [], 'no script errors');
    console.log(JSON.stringify(report));
  } catch (e) {
    if (shots) { for (const c of browser.contexts()) for (const pg of c.pages()) { try { await pg.screenshot({path: path.join(shots, 'FAILED.png')}); } catch (e2) { /* closed */ } } }
    throw e;
  } finally { await browser.close().catch(() => {}); await mock.close(); }
}
main().catch(e => { console.error(e); process.exit(1); });

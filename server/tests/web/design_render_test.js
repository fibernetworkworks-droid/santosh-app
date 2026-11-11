/* HOOLA DESIGN - the renderer and the layout engine (hd-layout.js, hd-render.js) in a REAL browser, against the real
   hd-math.js / hd-core.js. Serves the static design folder itself, loads a scripted document that has every node
   type, paint and effect, and asserts on canvas pixels, hit tests and layout numbers; then measures frame times
   (5,000 mixed nodes while panning, 20,000 zoomed out).
   Run:  node server/tests/web/design_render_test.js          (DESIGN_SHOTS=<dir> also writes PNGs to look at)
   Exit 0 = pass, 1 = fail, 77 = could not run here (no playwright / no Chromium). The last line is a JSON report. */
'use strict';
const http = require('http'), fs = require('fs'), path = require('path'), assert = require('node:assert/strict');
const DESIGN = path.resolve(__dirname, '../../app/static/console/design');
const SHOTS = process.env.DESIGN_SHOTS || '';
const FILES = ['hd-math.js', 'hd-core.js', 'hd-layout.js', 'hd-render.js'];

/* ------------------------------------------------------------------ code that runs inside the page */
const IN_PAGE = `
window.T = {};
T.COL = ['#FF9A3C', '#C055F5', '#7C5CFF', '#2DD4BF', '#34D399', '#F87171', '#FFB15C', '#120E2A', '#3B82F6', '#EAB308'];
T.reset = function () {
  HD.store.load({nodes: {'0:0': {type: 'DOCUMENT'}, '0:1': {type: 'PAGE', parent: '0:0', idx: 'a', name: 'Page 1'}}}, 1);
  if (HD.sel.page !== '0:1') HD.sel.setPage('0:1');
  return '0:1';
};
T.rng = function (seed) { let s = seed >>> 0; return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; };
T.box = function (id) { const n = HD.store.get(id); return [n.x || 0, n.y || 0, HD.store.prop(id, 'w'), HD.store.prop(id, 'h')].map(v => Math.round(v * 100) / 100); };
T.px = function (sx, sy) { const c = HD.render.canvas, d = HD.render.dpr; const p = c.getContext('2d').getImageData(Math.round(sx * d), Math.round(sy * d), 1, 1).data; return [p[0], p[1], p[2]]; };
T.snap = function () { const c = HD.render.canvas; return c.getContext('2d').getImageData(0, 0, c.width, c.height).data; };
T.diff = function (a, b) { let small = 0, big = 0; for (let i = 0; i < a.length; i += 4) { const d = Math.max(Math.abs(a[i] - b[i]), Math.abs(a[i + 1] - b[i + 1]), Math.abs(a[i + 2] - b[i + 2])); if (d > 24) small++; if (d > 100) big++; } return {small, big}; };
T.stat = function (a) { const s = a.slice().sort((x, y) => x - y), sum = a.reduce((x, y) => x + y, 0); const r = v => Math.round(v * 100) / 100; return {avg: r(sum / a.length), p50: r(s[s.length >> 1]), p90: r(s[Math.floor(s.length * 0.9)]), max: r(s[s.length - 1])}; };
/* n mixed nodes: cards (a frame with rects, texts, ellipses, lines; every 4th with a shadow) or, flat, everything on the page */
T.mixed = function (n, flat, seed) {
  const S = HD.store, pg = T.reset(), C = T.COL;
  const cols = Math.ceil(Math.sqrt(n / (flat ? 1 : 10)) * 1.3);
  let made = 0, i = 0;
  S.tx('gen', () => {
    while (made < n) {
      const cx = (i % cols) * (flat ? 60 : 260), cy = Math.floor(i / cols) * (flat ? 60 : 200); i++;
      if (flat) {
        const k = made % 5, c = C[made % C.length];
        if (k === 0) S.create('RECT', pg, {x: cx, y: cy, w: 44, h: 40, fills: [{type: 'solid', color: c}], radius: made % 3 ? 0 : 8});
        else if (k === 1) S.create('ELLIPSE', pg, {x: cx, y: cy, w: 44, h: 40, fills: [{type: 'solid', color: c}], strokes: [{type: 'solid', color: '#120E2A'}], strokeWeight: 2});
        else if (k === 2) S.create('TEXT', pg, {x: cx, y: cy, chars: 'Label ' + made, fontSize: 12, fills: [{type: 'solid', color: '#120E2A'}]});
        else if (k === 3) S.create('STAR', pg, {x: cx, y: cy, w: 40, h: 40, fills: [{type: 'solid', color: c}], rot: (made * 7) % 360});
        else S.create('RECT', pg, {x: cx, y: cy, w: 44, h: 40, fills: [{type: 'linear', stops: [{pos: 0, color: c}, {pos: 1, color: '#FFFFFF'}]}], opacity: 0.8});
        made++;
        continue;
      }
      const f = S.create('FRAME', pg, {x: cx, y: cy, w: 230, h: 170, name: 'Card ' + i, fills: [{type: 'solid', color: '#FFFFFF'}], radius: 12,
        effects: i % 4 === 0 ? [{type: 'drop', x: 0, y: 4, blur: 12, spread: 0, color: '#000000', opacity: 0.2}] : undefined});
      made++;
      const kids = Math.min(9, n - made);
      for (let k = 0; k < kids; k++) {
        const c = C[(made + k) % C.length], x = 12 + (k % 3) * 72, y = 12 + Math.floor(k / 3) * 52;
        if (k % 4 === 0) S.create('RECT', f, {x, y, w: 60, h: 40, fills: [{type: 'solid', color: c}], radius: 6});
        else if (k % 4 === 1) S.create('TEXT', f, {x, y, chars: 'Item ' + (made + k), fontSize: 13, fills: [{type: 'solid', color: '#120E2A'}]});
        else if (k % 4 === 2) S.create('ELLIPSE', f, {x, y, w: 40, h: 40, fills: [{type: 'solid', color: c}], strokes: [{type: 'solid', color: '#120E2A'}], strokeWeight: 1.5});
        else S.create('LINE', f, {x, y: y + 20, w: 60, strokes: [{type: 'solid', color: c}], strokeWeight: 3});
      }
      made += kids;
    }
  });
  return made;
};
/* pan by (dx, dy) screen px per frame; ms per frame around flush() + a one pixel read-back (so the raster is in the number) */
T.pan = function (frames, dx, dy) {
  const R = HD.render, out = [], c = R.canvas.getContext('2d');
  for (let i = 0; i < frames; i++) { const v = R.view, t = performance.now(); R.setView({x: v.x + dx, y: v.y + dy, zoom: v.zoom}); R.flush(); c.getImageData(0, 0, 1, 1); out.push(performance.now() - t); }
  return out;
};
T.gallery = function () {
  const S = HD.store, pg = T.reset(), ids = {};
  const solid = c => [{type: 'solid', color: c}];
  S.tx('gallery', () => {
    ids.sIn = S.create('RECT', pg, {x: 20, y: 20, w: 80, h: 60, fills: solid('#FFFFFF'), strokes: solid('#FF0000'), strokeWeight: 10, strokeAlign: 'inside'});
    ids.sCe = S.create('RECT', pg, {x: 130, y: 20, w: 80, h: 60, fills: solid('#FFFFFF'), strokes: solid('#FF0000'), strokeWeight: 10, strokeAlign: 'center'});
    ids.sOut = S.create('RECT', pg, {x: 240, y: 20, w: 80, h: 60, fills: solid('#FFFFFF'), strokes: solid('#FF0000'), strokeWeight: 10, strokeAlign: 'outside'});
    ids.pIn = S.create('POLYGON', pg, {x: 350, y: 20, w: 80, h: 60, sides: 3, fills: solid('#FFFFFF'), strokes: solid('#0000FF'), strokeWeight: 8, strokeAlign: 'inside'});
    ids.pOut = S.create('POLYGON', pg, {x: 460, y: 20, w: 80, h: 60, sides: 3, fills: solid('#FFFFFF'), strokes: solid('#0000FF'), strokeWeight: 8, strokeAlign: 'outside', strokeJoin: 'round'});
    ids.eDash = S.create('ELLIPSE', pg, {x: 570, y: 20, w: 80, h: 60, strokes: solid('#120E2A'), strokeWeight: 3, dash: [6, 4]});
    ids.multi = S.create('RECT', pg, {x: 680, y: 20, w: 80, h: 60, radius: 12, fills: [{type: 'solid', color: '#FFFF00'}, {type: 'linear', stops: [{pos: 0, color: '#FF0000', opacity: 1}, {pos: 1, color: '#FF0000', opacity: 0}], from: [0, 0.5], to: [1, 0.5]}, {type: 'solid', color: '#000000', visible: false}]});
    ids.drop = S.create('RECT', pg, {x: 20, y: 120, w: 80, h: 60, radius: 8, fills: solid('#FFFFFF'), effects: [{type: 'drop', x: 8, y: 8, blur: 0, spread: 0, color: '#000000', opacity: 1}]});
    ids.dropSoft = S.create('ELLIPSE', pg, {x: 130, y: 120, w: 80, h: 60, fills: solid('#FFB15C'), effects: [{type: 'drop', x: 0, y: 6, blur: 12, spread: 4, color: '#7C5CFF', opacity: 0.8}]});
    ids.inner = S.create('RECT', pg, {x: 240, y: 120, w: 80, h: 60, fills: solid('#FFFFFF'), effects: [{type: 'inner', x: 6, y: 6, blur: 0, color: '#FF0000', opacity: 1}]});
    ids.blur = S.create('RECT', pg, {x: 350, y: 120, w: 80, h: 60, fills: solid('#0000FF'), effects: [{type: 'blur', blur: 8}]});
    ids.txtShadow = S.create('TEXT', pg, {x: 460, y: 125, chars: 'Shadow', fontSize: 26, fontWeight: 700, fills: solid('#120E2A'), effects: [{type: 'drop', x: 3, y: 3, blur: 2, color: '#FF0000', opacity: 1}]});
    ids.stripes = S.create('FRAME', pg, {x: 570, y: 110, w: 200, h: 80, fills: solid('#FFFFFF'), name: 'Glass'});
    for (let i = 0; i < 10; i++) S.create('RECT', ids.stripes, {x: i * 20, y: 0, w: 10, h: 80, fills: solid('#000000')});
    ids.glass = S.create('RECT', ids.stripes, {x: 60, y: 15, w: 120, h: 50, radius: 10, fills: [{type: 'solid', color: '#FFFFFF', opacity: 0.2}], effects: [{type: 'bgblur', blur: 16}]});
    ids.grp = S.create('FRAME', pg, {x: 20, y: 220, w: 100, h: 80, opacity: 0.5, clip: false, name: 'Half'});
    ids.grpA = S.create('RECT', ids.grp, {x: 0, y: 0, w: 60, h: 60, fills: solid('#FF0000')});
    ids.grpB = S.create('RECT', ids.grp, {x: 30, y: 20, w: 60, h: 60, fills: solid('#0000FF')});
    ids.blendBase = S.create('RECT', pg, {x: 150, y: 220, w: 80, h: 80, fills: solid('#FFFF00')});
    ids.blend = S.create('RECT', pg, {x: 190, y: 240, w: 80, h: 40, fills: solid('#00FFFF'), blend: 'multiply'});
    ids.mgroup = S.create('GROUP', pg, {x: 300, y: 220});
    ids.mask = S.create('ELLIPSE', ids.mgroup, {x: 0, y: 0, w: 80, h: 80, fills: solid('#000000'), mask: true});
    ids.masked = S.create('RECT', ids.mgroup, {x: 0, y: 0, w: 80, h: 80, fills: [{type: 'linear', stops: [{pos: 0, color: '#FF0000'}, {pos: 1, color: '#0000FF'}], from: [0, 0], to: [1, 0]}]});
    ids.tmaskG = S.create('GROUP', pg, {x: 400, y: 220});
    ids.tmask = S.create('TEXT', ids.tmaskG, {x: 0, y: 0, chars: 'MASK', fontSize: 40, fontWeight: 900, fills: solid('#000000'), mask: true});
    ids.tmasked = S.create('RECT', ids.tmaskG, {x: 0, y: 0, w: 140, h: 50, fills: solid('#FF0000')});
    ids.rot = S.create('RECT', pg, {x: 570, y: 230, w: 80, h: 40, rot: 30, fills: solid('#34D399'), strokes: solid('#120E2A'), strokeWeight: 2});
    ids.flip = S.create('VECTOR', pg, {x: 680, y: 220, w: 60, h: 60, flipH: true, path: 'M0 0 L60 30 L0 60 Z', fills: solid('#F87171')});
    ids.vecScaled = S.create('VECTOR', pg, {x: 760, y: 220, w: 100, h: 30, path: 'M0 0 L50 0 L50 50 L0 50 Z M10 10 L10 40 L40 40 L40 10 Z', fillRule: 'evenodd', fills: solid('#7C5CFF')});
    ids.tCenter = S.create('TEXT', pg, {x: 20, y: 330, w: 200, autoResize: 'h', align: 'center', chars: 'Centered text that wraps on two lines', fontSize: 16, fills: solid('#120E2A')});
    ids.tRight = S.create('TEXT', pg, {x: 240, y: 330, w: 160, h: 70, autoResize: 'none', align: 'right', alignV: 'bottom', chars: 'Right bottom', fontSize: 16, fills: solid('#120E2A'), decoration: 'underline'});
    ids.tRuns = S.create('TEXT', pg, {x: 420, y: 330, chars: 'Plain BOLD red big', fontSize: 16, fills: solid('#120E2A'), runs: [{s: 6, e: 10, fontWeight: 800}, {s: 11, e: 14, fills: [{type: 'solid', color: '#FF0000'}], decoration: 'strike'}, {s: 15, e: 18, fontSize: 30}]});
    ids.tCase = S.create('TEXT', pg, {x: 420, y: 380, chars: 'upper case spaced', fontSize: 14, textCase: 'upper', letterSpacing: 4, fills: solid('#120E2A')});
    ids.tJust = S.create('TEXT', pg, {x: 640, y: 330, w: 180, autoResize: 'h', align: 'justify', lineHeight: 24, chars: 'Justified text spreads its words to both edges of the box nicely', fontSize: 14, fills: solid('#120E2A')});
    ids.tStroke = S.create('TEXT', pg, {x: 20, y: 400, chars: 'Outline', fontSize: 36, fontWeight: 800, fills: solid('#FFFFFF'), strokes: solid('#7C5CFF'), strokeWeight: 3, strokeAlign: 'outside'});
    ids.tBig = S.create('TEXT', pg, {x: 200, y: 400, chars: 'Hxg', fontSize: 48, fills: solid('#000000')});
    ids.imFill = S.create('RECT', pg, {x: 20, y: 470, w: 100, h: 100, radius: 20, fills: [{type: 'image', hash: 'quadquadquad', mode: 'fill'}]});
    ids.imFit = S.create('RECT', pg, {x: 140, y: 470, w: 100, h: 100, fills: [{type: 'solid', color: '#DDDDDD'}, {type: 'image', hash: 'quadquadquad', mode: 'fit'}]});
    ids.imCrop = S.create('ELLIPSE', pg, {x: 260, y: 470, w: 100, h: 100, fills: [{type: 'image', hash: 'quadquadquad', mode: 'crop', crop: [0, 0, 0.5, 0.5]}]});
    ids.imTile = S.create('RECT', pg, {x: 380, y: 470, w: 150, h: 100, fills: [{type: 'image', hash: 'quadquadquad', mode: 'tile', scale: 0.5}]});
    ids.comp = S.create('COMPONENT', pg, {x: 560, y: 470, w: 120, h: 44, name: 'Button', radius: 22, fills: solid('#7C5CFF')});
    ids.compLabel = S.create('TEXT', ids.comp, {x: 30, y: 12, chars: 'Button', fontSize: 16, fontWeight: 600, fills: solid('#FFFFFF')});
    ids.compDot = S.create('ELLIPSE', ids.comp, {x: 8, y: 14, w: 16, h: 16, fills: solid('#FFB15C')});
    ids.inst = S.create('INSTANCE', pg, {x: 700, y: 470, w: 120, h: 44, comp: ids.comp, name: 'Button', ov: {[ids.compLabel]: {chars: 'Save'}, [ids.compDot]: {fills: solid('#00FF00')}}});
    ids.inst2 = S.create('INSTANCE', pg, {x: 560, y: 530, w: 240, h: 88, comp: ids.comp, fills: solid('#120E2A'), name: 'Big'});
    ids.sect = S.create('SECTION', pg, {x: 880, y: 20, w: 200, h: 160, name: 'Section', fills: [{type: 'solid', color: '#7C5CFF', opacity: 0.1}]});
    ids.locked = S.create('RECT', pg, {x: 900, y: 220, w: 60, h: 60, fills: solid('#000000'), locked: true});
    ids.hidden = S.create('RECT', pg, {x: 980, y: 220, w: 60, h: 60, fills: solid('#000000'), visible: false});
    ids.hollow = S.create('RECT', pg, {x: 900, y: 320, w: 80, h: 80, strokes: solid('#000000'), strokeWeight: 2});
    ids.line = S.create('LINE', pg, {x: 900, y: 460, w: 120, strokes: solid('#000000'), strokeWeight: 4});
    ids.star = S.create('STAR', pg, {x: 1000, y: 320, w: 80, h: 80, sides: 5, ratio: 0.4, fills: solid('#FFB15C')});
    ids.clipF = S.create('FRAME', pg, {x: 900, y: 520, w: 100, h: 80, name: 'Clip', fills: solid('#FFFFFF')});
    ids.clipKid = S.create('RECT', ids.clipF, {x: 60, y: 20, w: 100, h: 40, fills: solid('#3B82F6')});
    ids.radial = S.create('ELLIPSE', pg, {x: 1040, y: 220, w: 60, h: 60, fills: [{type: 'radial', stops: [{pos: 0, color: '#FFFFFF'}, {pos: 1, color: '#FF0000'}], from: [0.5, 0.5], to: [1, 0.5]}]});
    ids.angular = S.create('RECT', pg, {x: 1040, y: 420, w: 60, h: 60, fills: [{type: 'angular', stops: [{pos: 0, color: '#FF0000'}, {pos: 0.5, color: '#0000FF'}, {pos: 1, color: '#FF0000'}], from: [0.5, 0.5], to: [1, 0.5]}]});
    ids.xml = S.create('TEXT', pg, {x: 880, y: 620, chars: '<b>R&D "q" \\'s\\'</b>', fontSize: 12, fills: solid('#120E2A')});
  });
  return ids;
};
`;

/* ------------------------------------------------------------------ the little server + browser */
function serve(png) {
  const server = http.createServer((req, res) => {
    const p = new URL(req.url, 'http://x').pathname;
    if (p === '/t.html') {
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'");
      return res.end('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;height:100%;overflow:hidden}#c{position:absolute;inset:0;width:100%;height:100%}</style></head><body><canvas id="c"></canvas>' +
        FILES.map(f => '<script src="/d/' + f + '"></script>').join('') + '<script src="/inpage.js"></script></body></html>');
    }
    if (p === '/inpage.js') { res.setHeader('Content-Type', 'application/javascript; charset=utf-8'); return res.end(IN_PAGE); }
    if (p.startsWith('/api/design/assets/')) {
      if (!/^Bearer fixture$/.test(req.headers.authorization || '')) { res.writeHead(401); return res.end(); }
      res.setHeader('Content-Type', 'image/png');
      return res.end(png);
    }
    if (p.startsWith('/d/')) {
      const f = path.join(DESIGN, p.slice(3));
      if (f.startsWith(DESIGN) && fs.existsSync(f)) { res.setHeader('Content-Type', 'application/javascript; charset=utf-8'); return res.end(fs.readFileSync(f)); }
    }
    res.writeHead(404); res.end();
  });
  return new Promise(r => server.listen(0, '127.0.0.1', () => r(server)));
}
const near = (a, b, tol) => a.every((v, i) => Math.abs(v - b[i]) <= (tol === undefined ? 6 : tol));
function isColor(got, want, msg, tol) { assert.ok(near(got, want, tol), msg + ': got rgb(' + got + ') want rgb(' + want + ')'); }

async function main() {
  let chromium;
  try { ({chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright')); } catch (e) { console.log('SKIP: playwright is not installed'); process.exit(77); }
  const exe = process.env.HOOLA_CHROMIUM || process.env.CHROMIUM_EXECUTABLE || undefined;
  let browser;
  try { browser = await chromium.launch({executablePath: exe, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']}); }
  catch (e) { console.log('SKIP: Chromium can not start here: ' + String(e.message).split('\n')[0]); process.exit(77); }
  const report = {checks: 0, perf: {}};
  const ok = (name) => { report.checks++; if (process.env.DESIGN_VERBOSE) console.log('ok  ' + name); };
  let server = null;
  try {
    /* a 64x48 picture with four coloured quarters, made by the browser itself */
    const mk = await browser.newPage();
    const quad = Buffer.from(await mk.evaluate(() => { const c = document.createElement('canvas'); c.width = 64; c.height = 48; const x = c.getContext('2d'); x.fillStyle = '#FF0000'; x.fillRect(0, 0, 32, 24); x.fillStyle = '#00FF00'; x.fillRect(32, 0, 32, 24); x.fillStyle = '#0000FF'; x.fillRect(0, 24, 32, 24); x.fillStyle = '#FFFF00'; x.fillRect(32, 24, 32, 24); return c.toDataURL('image/png').split(',')[1]; }), 'base64');
    await mk.close();
    server = await serve(quad);
    const url = 'http://127.0.0.1:' + server.address().port + '/t.html';
    const open = async (w, h, dpr) => {
      const page = await browser.newPage({viewport: {width: w, height: h}, deviceScaleFactor: dpr || 1});
      const errors = [];
      page.on('pageerror', e => errors.push(String(e.stack || e.message)));
      page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push('console: ' + m.text()); });
      await page.addInitScript(() => { try { localStorage.setItem('hoola.console.token', 'fixture'); } catch (e) { /* no storage */ } });
      await page.goto(url);
      await page.evaluate(() => { HD.render.webFonts = false; HD.render.zoomPreview = false; HD.render.init(document.getElementById('c')); });
      return {page, errors};
    };
    const shot = async (page, name) => { if (SHOTS) { fs.mkdirSync(SHOTS, {recursive: true}); await page.screenshot({path: path.join(SHOTS, name + '.png')}); } };

    /* ================================================================ 1. the contract is all there */
    const A = await open(1120, 680, 1), p = A.page;
    const api = await p.evaluate(() => ({
      render: ['init', 'setView', 'zoomToFit', 'invalidate', 'screenToWorld', 'worldToScreen', 'hitTest', 'nodesInRect', 'addOverlay', 'drawNode', 'toCanvas', 'toSVG', 'image'].filter(k => typeof HD.render[k] !== 'function'),
      layout: ['run', 'measureText'].filter(k => typeof HD.layout[k] !== 'function'),
      view: HD.render.view && typeof HD.render.view.zoom === 'number'
    }));
    assert.deepEqual(api, {render: [], layout: [], view: true}); ok('contract');

    /* ================================================================ 2. layout numbers */
    const lay = await p.evaluate(() => {
      const S = HD.store, pg = T.reset(), o = {}, box = T.box;
      let t1, t2, t3;
      S.tx('t', () => {
        t1 = S.create('TEXT', pg, {x: 0, y: 0, chars: 'Hello world', fontSize: 20});
        t2 = S.create('TEXT', pg, {x: 0, y: 50, w: 120, autoResize: 'h', chars: 'The quick brown fox jumps over the lazy dog', fontSize: 16});
        t3 = S.create('TEXT', pg, {x: 0, y: 200, w: 80, h: 30, autoResize: 'none', chars: 'fixed box text that overflows', fontSize: 16});
      });
      const m1 = HD.layout.measureText(S.get(t1)), m2 = HD.layout.measureText(S.get(t2));
      o.t1 = box(t1); o.m1 = [m1.w, m1.h, m1.lines.length, m1.lineHeight]; o.t2 = box(t2); o.m2 = {n: m2.lines.length, widest: Math.max.apply(null, m2.lines.map(l => l.w)), h: m2.h, lh: m2.lineHeight, joined: m2.lines.map(l => l.text.trim()).join(' ')}; o.t3 = box(t3);
      S.tx('nl', () => S.set(t1, {chars: 'Hello\nworld\n'}));
      o.t1nl = [box(t1)[3], HD.layout.measureText(S.get(t1)).lines.length];
      S.tx('up', () => S.set(t1, {chars: 'Hello world', textCase: 'upper', letterSpacing: 2}));
      o.t1up = box(t1)[2];
      /* auto layout: fixed + fill + hug text, hugging its cross axis */
      let f, a, b, c, d;
      S.tx('al', () => {
        f = S.create('FRAME', pg, {x: 300, y: 0, w: 400, h: 100, sizeV: 'hug', layout: {mode: 'h', gap: 10, pad: [8, 16, 8, 16], alignMain: 'start', alignCross: 'center', wrap: false}});
        a = S.create('RECT', f, {w: 50, h: 40});
        b = S.create('RECT', f, {w: 10, h: 60, sizeH: 'fill'});
        c = S.create('TEXT', f, {chars: 'Label', fontSize: 16});
      });
      o.cw = box(c)[2]; o.ch = box(c)[3];
      o.al1 = {f: box(f), a: box(a), b: box(b), c: box(c)};
      S.tx('resize', () => S.set(f, {w: 500})); o.al2 = {b: box(b), c: box(c)};
      S.tx('max', () => S.set(b, {maxW: 100})); o.al3 = {b: box(b), c: box(c)};
      S.tx('between', () => S.set(f, {layout: Object.assign({}, S.get(f).layout, {alignMain: 'between'})})); o.al4 = {a: box(a), b: box(b), c: box(c)};
      S.tx('abs', () => { S.set(a, {visible: false}); d = S.create('RECT', f, {x: 300, y: 5, w: 20, h: 20, layoutPos: 'absolute', cons: {h: 'right', v: 'top'}}); S.set(f, {layout: Object.assign({}, S.get(f).layout, {alignMain: 'end'})}); });
      o.al5 = {a: box(a), b: box(b), c: box(c), d: box(d)};
      S.tx('resize2', () => S.set(f, {w: 600})); o.al6 = {d: box(d), c: box(c)};
      /* nested, bottom-up then top-down: a hugging row holds a hugging column whose text fills its width and wraps */
      let outer, col, tt, r1, last;
      S.tx('nest', () => {
        outer = S.create('FRAME', pg, {x: 0, y: 300, sizeH: 'hug', sizeV: 'hug', layout: {mode: 'h', gap: 12, pad: [10, 10, 10, 10]}});
        col = S.create('FRAME', outer, {w: 160, sizeV: 'hug', layout: {mode: 'v', gap: 6, pad: [4, 4, 4, 4], alignCross: 'stretch'}});
        r1 = S.create('RECT', col, {w: 30, h: 20});
        tt = S.create('TEXT', col, {chars: 'A paragraph that must wrap inside the column because it is long', fontSize: 14, sizeH: 'fill'});
        last = S.create('RECT', outer, {w: 40, h: 40, sizeV: 'fill'});
      });
      o.nest1 = {outer: box(outer), col: box(col), r1: box(r1), tt: box(tt), last: box(last), lines: HD.layout.measureText(S.get(tt)).lines.length};
      S.tx('grow', () => S.set(col, {w: 600}));
      o.nest2 = {outer: box(outer), col: box(col), r1: box(r1), tt: box(tt), last: box(last), lines: HD.layout.measureText(S.get(tt)).lines.length};
      S.tx('del', () => S.remove([r1]));
      o.nest3 = {col: box(col), tt: box(tt)};
      /* wrap */
      let wr; const wk = [];
      S.tx('wrap', () => { wr = S.create('FRAME', pg, {x: 0, y: 450, w: 130, sizeV: 'hug', layout: {mode: 'h', gap: 10, pad: [5, 5, 5, 5], wrap: true}}); for (let i = 0; i < 5; i++) wk.push(S.create('RECT', wr, {w: 50, h: 20 + i * 5})); });
      o.wrap = {wr: box(wr), kids: wk.map(box)};
      /* constraints */
      let cf; const ck = {};
      S.tx('cons', () => {
        cf = S.create('FRAME', pg, {x: 500, y: 300, w: 200, h: 100});
        ck.l = S.create('RECT', cf, {x: 10, y: 10, w: 20, h: 20});
        ck.r = S.create('RECT', cf, {x: 170, y: 10, w: 20, h: 20, cons: {h: 'right', v: 'bottom'}});
        ck.lr = S.create('RECT', cf, {x: 10, y: 40, w: 180, h: 20, cons: {h: 'leftright', v: 'topbottom'}});
        ck.c = S.create('RECT', cf, {x: 90, y: 70, w: 20, h: 20, cons: {h: 'center', v: 'center'}});
        ck.s = S.create('RECT', cf, {x: 50, y: 50, w: 100, h: 20, cons: {h: 'scale', v: 'scale'}});
      });
      const all = () => Object.fromEntries(Object.entries(ck).map(([k, v]) => [k, box(v)]));
      o.cons0 = all();
      S.tx('rs', () => S.set(cf, {w: 300, h: 150})); o.cons1 = all();
      S.undo(); o.consUndo = all(); o.cfUndo = box(cf);
      S.redo(); o.consRedo = all();
      S.tx('rs2', () => S.set(cf, {w: 200, h: 100})); o.cons2 = all();
      /* group bounds */
      let g, g1, g2;
      S.tx('grp', () => { g = S.create('GROUP', pg, {x: 0, y: 0}); g1 = S.create('RECT', g, {x: 700, y: 400, w: 40, h: 40}); g2 = S.create('RECT', g, {x: 760, y: 430, w: 30, h: 50}); });
      const wb = id => { const r = S.worldBounds(id); return [r.x, r.y, r.w, r.h].map(v => Math.round(v * 100) / 100); };
      o.grp1 = {g: box(g), g1: box(g1), g2: box(g2)};
      S.tx('mv', () => S.set(g1, {x: -20, y: -10})); o.grp2 = {g: box(g), g1: box(g1), g2: box(g2), w1: wb(g1), w2: wb(g2)};
      S.tx('rot', () => S.set(g, {rot: 90})); const before = wb(g2);
      S.tx('mv2', () => S.set(g2, {x: S.get(g2).x + 50})); o.grp3 = {same: JSON.stringify(wb(g1)) === JSON.stringify([680, 390, 40, 40]) || wb(g1), g1: box(g1), gw: box(g)[2], moved: wb(g2), before};
      S.tx('rm', () => { S.set(g, {rot: 0}); }); S.tx('rm2', () => S.remove([g1])); o.grp4 = {g: box(g).slice(2), g2: box(g2)};
      return o;
    });
    assert.ok(lay.t1[2] > 60 && lay.t1[2] < 200 && lay.t1[3] === 24, 'a wh text hugs its words: ' + lay.t1);
    assert.deepEqual(lay.m1.slice(0, 3), [lay.t1[2], lay.t1[3], 1]); assert.equal(lay.m1[3], 24);
    assert.ok(lay.t2[2] === 120 && lay.m2.n >= 3 && lay.m2.widest <= 120.01 && lay.t2[3] === Math.round(lay.m2.n * 19.2 * 100) / 100, 'an h text wraps inside its width and grows down: ' + JSON.stringify(lay.m2));
    assert.equal(lay.m2.joined, 'The quick brown fox jumps over the lazy dog');
    assert.deepEqual(lay.t3, [0, 200, 80, 30]);
    assert.deepEqual(lay.t1nl, [72, 3]);
    assert.ok(lay.t1up > lay.t1[2], 'upper case + letter spacing is wider');
    const cw = lay.cw;
    assert.deepEqual(lay.al1, {f: [300, 0, 400, 76], a: [16, 18, 50, 40], b: [76, 8, Math.round((400 - 32 - 50 - 20 - cw) * 100) / 100, 60], c: [400 - 16 - cw, Math.round((8 + (60 - lay.ch) / 2) * 100) / 100, cw, lay.ch]});
    assert.equal(lay.al2.b[2], 500 - 32 - 50 - 20 - cw);
    assert.deepEqual([lay.al3.b[2], lay.al3.c[0]], [100, 186]);
    assert.deepEqual([lay.al4.a[0], lay.al4.b[0], lay.al4.c[0]], [16, Math.round((16 + 50 + (468 - 150 - cw) / 2) * 100) / 100, 500 - 16 - cw]);
    assert.deepEqual([lay.al5.b[0], lay.al5.c[0], lay.al5.d], [500 - 16 - cw - 10 - 100, 500 - 16 - cw, [300, 5, 20, 20]]);
    assert.deepEqual([lay.al6.d, lay.al6.c[0]], [[400, 5, 20, 20], 600 - 16 - cw]);
    assert.ok(lay.nest1.lines >= 2 && lay.nest1.tt[2] === 152 && lay.nest1.r1[2] === 152, JSON.stringify(lay.nest1));
    assert.deepEqual(lay.nest1.col, [10, 10, 160, Math.round((4 + 20 + 6 + lay.nest1.tt[3] + 4) * 100) / 100]);
    assert.deepEqual(lay.nest1.outer, [0, 300, 232, Math.round((lay.nest1.col[3] + 20) * 100) / 100]);
    assert.deepEqual(lay.nest1.last, [182, 10, 40, lay.nest1.col[3]]);
    assert.ok(lay.nest2.lines < lay.nest1.lines && lay.nest2.tt[2] === 592 && lay.nest2.col[3] < lay.nest1.col[3] && lay.nest2.outer[2] === 672 && lay.nest2.last[3] === lay.nest2.col[3] && lay.nest2.last[0] === 622, JSON.stringify(lay.nest2));
    assert.deepEqual([lay.nest3.tt[1], lay.nest3.col[3]], [4, Math.round((lay.nest3.tt[3] + 8) * 100) / 100]);
    assert.deepEqual(lay.wrap, {wr: [0, 450, 130, 130], kids: [[5, 5, 50, 20], [65, 5, 50, 25], [5, 40, 50, 30], [65, 40, 50, 35], [5, 85, 50, 40]]});
    assert.deepEqual(lay.cons1, {l: [10, 10, 20, 20], r: [270, 60, 20, 20], lr: [10, 40, 280, 70], c: [140, 95, 20, 20], s: [75, 75, 150, 30]});
    assert.deepEqual(lay.consUndo, lay.cons0); assert.deepEqual(lay.cfUndo, [500, 300, 200, 100]);
    assert.deepEqual(lay.consRedo, lay.cons1); assert.deepEqual(lay.cons2, lay.cons0);
    assert.deepEqual(lay.grp1, {g: [700, 400, 90, 80], g1: [0, 0, 40, 40], g2: [60, 30, 30, 50]});
    assert.deepEqual(lay.grp2, {g: [680, 390, 110, 90], g1: [0, 0, 40, 40], g2: [80, 40, 30, 50], w1: [680, 390, 40, 40], w2: [760, 430, 30, 50]});
    assert.ok(Math.abs(lay.grp3.moved[1] - (lay.grp3.before[1] + 50)) < 0.02 && Math.abs(lay.grp3.moved[0] - lay.grp3.before[0]) < 0.02 && lay.grp3.gw === 160, 'a turned group hugs its children and they stay where they are: ' + JSON.stringify(lay.grp3));
    assert.deepEqual(lay.grp4, {g: [30, 50], g2: [0, 0, 30, 50]});
    ok('layout');

    /* ================================================================ 3. every node type, paint and effect: pixels */
    const ids = await p.evaluate(async () => { const ids = T.gallery(); HD.render.setView({x: 0, y: 0, zoom: 1}); HD.render.flush(); await HD.render.ready(HD.sel.page); HD.render.flush(); return ids; });
    await p.waitForTimeout(120);
    await p.evaluate(() => HD.render.flush());
    await shot(p, 'gallery');
    const px = (pts) => p.evaluate((pts) => pts.map(q => T.px(q[0], q[1])), pts);
    const BG = [245, 245, 245], RED = [255, 0, 0], WHITE = [255, 255, 255], BLUE = [0, 0, 255], BLACK = [0, 0, 0];
    let c = await px([[25, 50], [15, 50], [60, 50], [127, 50], [133, 50], [122, 50], [235, 50], [245, 50], [228, 50],        // stroke inside / center / outside
      [376, 74], [390, 55], [352, 78], [458, 82], [500, 84], [500, 50],                                                    // polygon inside / outside
      [686, 50], [756, 50], [682, 22],                                                                                     // stacked fills + radius
      [104, 184], [60, 150], [112, 150], [243, 150], [300, 170], [322, 150],                                               // hard drop, inner
      [390, 150], [346, 150], [330, 150],                                                                                  // layer blur
      [170, 191], [170, 150]]);                                                                                            // soft shadow with spread
    isColor(c[0], RED, 'inside stroke lies inside the box'); isColor(c[1], BG, 'inside stroke does not leave the box'); isColor(c[2], WHITE, 'fill');
    isColor(c[3], RED, 'center stroke, outer half'); isColor(c[4], RED, 'center stroke, inner half'); isColor(c[5], BG, 'center stroke ends 5px out');
    isColor(c[6], RED, 'outside stroke lies outside the box'); isColor(c[7], WHITE, 'outside stroke keeps the inside clean'); isColor(c[8], BG, 'outside stroke ends 10px out');
    isColor(c[9], BLUE, 'polygon inside stroke along the bottom edge'); isColor(c[10], WHITE, 'polygon fill'); isColor(c[11], BLUE, 'polygon inside stroke stays inside the corner');
    isColor(c[12], BLUE, 'polygon outside stroke reaches past the corner'); isColor(c[13], BLUE, 'polygon outside stroke below the edge'); isColor(c[14], WHITE, 'polygon outside stroke keeps the fill');
    assert.ok(c[15][0] > 240 && c[15][1] < 40, 'a gradient that fades out, over a solid: red on the left ' + c[15]); isColor(c[16], [255, 255, 0], 'yellow on the right', 20); isColor(c[17], BG, 'radius cuts the corner');
    isColor(c[18], BLACK, 'hard drop shadow, bottom right'); isColor(c[19], WHITE, 'the box above its shadow'); isColor(c[20], BG, 'the shadow ends');
    isColor(c[21], RED, 'inner shadow on the left edge'); isColor(c[22], WHITE, 'inner shadow leaves the middle'); isColor(c[23], BG, 'inner shadow stays inside');
    isColor(c[24], BLUE, 'layer blur keeps the middle', 12); assert.ok(c[25][2] > c[25][0] + 10 && c[25][0] < 235, 'layer blur bleeds past the edge ' + c[25]); isColor(c[26], BG, 'layer blur ends');
    assert.ok(c[27][2] > c[27][0] + 20 && c[27][0] < 230, 'soft violet shadow under the ellipse ' + c[27]); isColor(c[28], [255, 177, 92], 'ellipse fill');
    c = await px([[30, 230], [60, 250], [100, 290], [200, 260], [250, 260], [160, 230],                                     // group opacity, blend
      [302, 222], [312, 260], [368, 260], [538, 222], [610, 250], [571, 266], [649, 233],                                   // masks, rotation
      [685, 250], [735, 225], [685, 225], [810, 235], [770, 235],                                                           // flip, scaled even-odd path
      [650, 150], [690, 150], [760, 150]]);                                                                                 // background blur
    isColor(c[0], [250, 122, 122], 'red at half opacity'); isColor(c[1], [122, 122, 250], 'the group fades as ONE picture: blue hides red, then both fade'); isColor(c[2], [122, 122, 250], 'a frame that does not clip shows what sticks out');
    isColor(c[3], [0, 255, 0], 'multiply: yellow x cyan'); isColor(c[4], [0, 245, 245], 'multiply over the page'); isColor(c[5], [255, 255, 0], 'yellow');
    isColor(c[6], BG, 'the mask cuts the corner off'); assert.ok(c[7][0] > 180 && c[7][2] < 80, 'masked gradient, left ' + c[7]); assert.ok(c[8][2] > 180 && c[8][0] < 80, 'masked gradient, right ' + c[8]);
    isColor(c[9], BG, 'a text mask shows the fill only inside the letters');
    isColor(c[10], [52, 211, 153], 'rotated box, centre'); isColor(c[11], BG, 'its unrotated corner is empty'); isColor(c[12], BG, 'its unrotated far corner is empty');
    isColor(c[13], [248, 113, 113], 'flipped triangle: the tip is on the left'); isColor(c[14], [248, 113, 113], 'flipped triangle: the base is on the right'); isColor(c[15], BG, 'flipped triangle: top left is empty');
    isColor(c[16], BG, 'even-odd hole, path scaled to the box'); isColor(c[17], [124, 92, 255], 'even-odd ring');
    assert.ok(c[18][0] > 60 && c[18][0] < 215 && c[19][0] > 60 && c[19][0] < 215 && Math.abs(c[18][0] - c[19][0]) < 70, 'background blur smears the stripes under the glass ' + c[18] + ' / ' + c[19]);
    assert.ok(near(c[20], BLACK, 8) || near(c[20], WHITE, 8), 'stripes outside the glass stay sharp ' + c[20]);
    const inkOfMask = await p.evaluate((id) => { const b = HD.store.worldBounds(id); let n = 0; for (let y = b.y; y < b.y + b.h; y += 2) for (let x = b.x; x < b.x + b.w; x += 2) { const q = T.px(x, y); if (q[0] > 200 && q[1] < 60) n++; } return n; }, ids.tmask);
    assert.ok(inkOfMask > 40, 'the masked fill is seen through the letters (' + inkOfMask + ')');
    c = await px([[40, 490], [100, 490], [40, 550], [100, 550], [22, 472], [190, 475], [160, 500], [220, 550], [310, 520], [288, 488],          // images
      [576, 492], [716, 492], [592, 574], [700, 600], [800, 480],                                                                              // component, instance, overrides
      [930, 250], [1010, 250], [940, 360], [900, 360], [960, 460], [930, 560], [1005, 560], [1070, 250], [1098, 250], [1090, 450], [1050, 450]]);
    isColor(c[0], RED, 'image fill: top left quarter'); isColor(c[1], [0, 255, 0], 'image fill: top right'); isColor(c[2], BLUE, 'image fill: bottom left'); isColor(c[3], [255, 255, 0], 'image fill: bottom right'); isColor(c[4], BG, 'image fill is cut by the radius');
    isColor(c[5], [221, 221, 221], 'image fit: letterbox shows the paint below'); isColor(c[6], RED, 'image fit: picture'); isColor(c[7], [255, 255, 0], 'image fit: bottom right');
    isColor(c[8], RED, 'image crop: only the chosen part'); isColor(c[9], RED, 'image crop fills the ellipse');
    isColor(c[10], [255, 177, 92], 'component dot'); isColor(c[11], [0, 255, 0], 'instance: the dot fill is overridden'); isColor(c[12], [255, 177, 92], 'a bigger instance scales the component'); isColor(c[13], [18, 14, 42], "an instance's own fill wins"); isColor(c[14], [124, 92, 255], 'instance keeps the component fill');
    isColor(c[15], BLACK, 'a locked node is drawn'); isColor(c[16], BG, 'a hidden node is not'); isColor(c[17], BG, 'a stroke-only box is empty inside'); isColor(c[18], BLACK, 'its stroke', 40); isColor(c[19], BLACK, 'a line');
    isColor(c[20], WHITE, 'frame fill'); isColor(c[21], BG, 'a clipping frame cuts its child'); isColor(c[22], WHITE, 'radial gradient: centre', 12); assert.ok(c[23][0] > 240 && c[23][1] < 40, 'radial gradient: rim ' + c[23]);
    assert.ok(c[24][0] > 200 && c[24][2] < 60, 'angular gradient starts red on the right ' + c[24]); assert.ok(c[25][2] > 200 && c[25][0] < 60, 'angular gradient is blue opposite ' + c[25]);
    /* text: the ink sits inside its box, on a baseline, in reading order */
    const ink = await p.evaluate((ids) => {
      const out = {};
      const scan = (id, pad) => { const b = HD.store.worldBounds(id); let x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1; for (let y = Math.floor(b.y) - pad; y < b.y + b.h + pad; y++) for (let x = Math.floor(b.x) - pad; x < b.x + b.w + pad; x++) { const q = T.px(x, y); if (q[0] + q[1] + q[2] < 500) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; } } return {box: [b.x, b.y, b.w, b.h], ink: [x0, y0, x1, y1]}; };
      out.big = scan(ids.tBig, 6); out.center = scan(ids.tCenter, 2); out.right = scan(ids.tRight, 2); out.just = scan(ids.tJust, 2);
      const lr = HD.layout.measureText(HD.store.get(ids.tRuns)); out.runs = {n: lr.lines.length, segs: lr.lines[0].segs.filter(s => !s.sp).map(s => [s.text, s.st.weight, s.st.size, !!s.st.fills]), base: lr.lines[0].base, h: lr.h};
      out.caseText = HD.layout.measureText(HD.store.get(ids.tCase)).lines[0].text;
      const lj = HD.layout.measureText(HD.store.get(ids.tJust)); out.justW = lj.lines.map(l => Math.round(l.w)); out.justLh = lj.lineHeight;
      return out;
    }, ids);
    const big = ink.big;
    assert.ok(big.ink[1] >= big.box[1] && big.ink[3] <= big.box[1] + big.box[3] + 1 && big.ink[0] >= big.box[0] - 2 && big.ink[2] <= big.box[0] + big.box[2] + 2, 'the glyphs sit inside the text box: ' + JSON.stringify(big));
    const capTop = (big.ink[1] - big.box[1]) / big.box[3], descBottom = (big.ink[3] - big.box[1]) / big.box[3];
    assert.ok(capTop > 0.08 && capTop < 0.4 && descBottom > 0.8 && descBottom <= 1.02, 'cap height and descender sit where a 1.2 line puts them: ' + capTop.toFixed(2) + ' / ' + descBottom.toFixed(2));
    const cMid = (ink.center.ink[0] + ink.center.ink[2]) / 2, cBox = ink.center.box[0] + ink.center.box[2] / 2;
    assert.ok(Math.abs(cMid - cBox) < 6, 'centered text is centered: ' + cMid + ' vs ' + cBox);
    assert.ok(Math.abs(ink.right.ink[2] - (ink.right.box[0] + ink.right.box[2])) < 4 && ink.right.ink[3] > ink.right.box[1] + ink.right.box[3] - 8 && ink.right.ink[1] > ink.right.box[1] + 30, 'right + bottom aligned text: ' + JSON.stringify(ink.right));
    assert.deepEqual(ink.runs.segs.map(s => s[0].trim()), ['Plain', 'BOLD', 'red', 'big']); assert.deepEqual(ink.runs.segs.map(s => s[1]), [400, 800, 400, 400]); assert.deepEqual(ink.runs.segs.map(s => s[2]), [16, 16, 16, 30]); assert.deepEqual(ink.runs.segs.map(s => s[3]), [false, false, true, false]);
    assert.equal(ink.runs.h, 36); assert.equal(ink.caseText, 'UPPER CASE SPACED');
    assert.ok(ink.justW.length >= 3 && ink.justW.slice(0, -1).every(w => w === 180) && ink.justLh === 24, 'justified lines reach both edges: ' + ink.justW);
    ok('pixels');

    /* ================================================================ 4. hit testing on real geometry */
    const hit = await p.evaluate((ids) => {
      const R = HD.render, h = (x, y, deep) => R.hitTest(x, y, {deep: !!deep});
      return {
        rectIn: h(60, 50), rectOut: h(5, 5),
        ellCorner: h(132, 122, true), ellMid: h(170, 150, true),
        triCorner: h(352, 22, true), triMid: h(390, 60, true),
        hollowIn: h(940, 360, true), hollowEdge: h(901, 360, true), hollowNear: h(897.5, 360, true),
        lineNear: h(960, 462.5, true), lineFar: h(960, 475, true),
        locked: h(930, 250, true), hidden: h(1010, 250, true),
        rotMid: h(610, 250, true), rotCorner: h(571, 266, true), rotTip: h(649, 233, true),
        frameKidShallow: h(575, 150), frameKidDeep: h(575, 150, true), frameBg: h(585, 112), frameBgDeep: h(585, 112, true),
        groupShallow: h(340, 260), groupDeep: h(340, 260, true), maskCut: h(302, 222, true),
        clipped: h(1005, 560, true), clipKid: h(980, 560, true),
        inst: h(760, 492, true), instShallow: h(716, 492), compDeep: h(576, 492, true), compShallow: h(576, 492),
        flipTip: h(685, 250, true), flipEmpty: h(685, 225, true), hole: h(810, 235, true), ring: h(770, 235, true),
        halfOverflow: h(100, 290, true), text: h(470, 140, true),
        chain: R.hitChain(575, 150),
        label: R.hitTest(575, 100, {deep: false}), noLabel: R.hitTest(575, 100, {labels: false})
      };
    }, ids);
    assert.equal(hit.rectIn, ids.sIn); assert.equal(hit.rectOut, null);
    assert.equal(hit.ellCorner, null, 'the corner of an ellipse box is empty'); assert.equal(hit.ellMid, ids.dropSoft);
    assert.equal(hit.triCorner, null, 'beside a triangle is empty'); assert.equal(hit.triMid, ids.pIn);
    assert.equal(hit.hollowIn, null, 'a stroke-only box is not hit in its middle'); assert.equal(hit.hollowEdge, ids.hollow); assert.equal(hit.hollowNear, ids.hollow, 'a thin stroke has a tolerance');
    assert.equal(hit.lineNear, ids.line); assert.equal(hit.lineFar, null);
    assert.equal(hit.locked, null); assert.equal(hit.hidden, null);
    assert.equal(hit.rotMid, ids.rot); assert.equal(hit.rotCorner, null, 'the unrotated corner misses a turned box'); assert.equal(hit.rotTip, null);
    assert.equal(hit.frameKidDeep, hit.frameKidShallow, 'the child of a top-level frame is what a first click gets'); assert.notEqual(hit.frameKidDeep, ids.stripes);
    assert.equal(hit.frameBg, ids.stripes); assert.equal(hit.frameBgDeep, ids.stripes);
    assert.equal(hit.groupShallow, ids.mgroup, 'a first click takes the whole group'); assert.equal(hit.groupDeep, ids.masked); assert.equal(hit.maskCut, null, 'a masked layer is only hit where the mask shows it');
    assert.equal(hit.clipped, null, 'what a frame clips away can not be clicked'); assert.equal(hit.clipKid, ids.clipKid);
    assert.equal(hit.inst, ids.inst, 'an instance is one thing'); assert.equal(hit.instShallow, ids.inst); assert.equal(hit.compDeep, ids.compDot); assert.equal(hit.compShallow, ids.compDot);
    assert.equal(hit.flipTip, ids.flip); assert.equal(hit.flipEmpty, null); assert.equal(hit.hole, null, 'the hole of an even-odd path'); assert.equal(hit.ring, ids.vecScaled);
    assert.equal(hit.halfOverflow, ids.grpB); assert.equal(hit.text, ids.txtShadow);
    assert.deepEqual(hit.chain.slice(0, 1), [ids.stripes]); assert.equal(hit.chain.length, 2);
    assert.equal(hit.label, ids.stripes, 'the name above a frame selects it'); assert.equal(hit.noLabel, null);
    const mq = await p.evaluate((ids) => {
      const R = HD.render, pg = HD.sel.page;
      return {a: R.nodesInRect({x: 10, y: 10, w: 320, h: 80}, pg), around: R.nodesInRect({x: 566, y: 100, w: 214, h: 100}, pg), part: R.nodesInRect({x: 565, y: 115, w: 30, h: 30}, pg),
        rotMiss: R.nodesInRect({x: 568, y: 262, w: 6, h: 6}, pg), rotHit: R.nodesInRect({x: 600, y: 240, w: 6, h: 6}, pg), lockedHidden: R.nodesInRect({x: 890, y: 210, w: 140, h: 80}, pg), neg: R.nodesInRect({x: 330, y: 90, w: -320, h: -80}, pg)};
    }, ids);
    assert.deepEqual(mq.a, [ids.sIn, ids.sCe, ids.sOut]); assert.deepEqual(mq.neg, mq.a);
    assert.deepEqual(mq.around, [ids.stripes], 'a frame wholly inside the marquee is taken as one'); assert.ok(mq.part.length === 2 && mq.part.indexOf(ids.stripes) < 0, 'a marquee inside a frame takes its children: ' + mq.part);
    assert.deepEqual(mq.rotMiss, [], 'the empty corner of a turned box is not selected'); assert.deepEqual(mq.rotHit, [ids.rot]); assert.deepEqual(mq.lockedHidden, []);
    ok('hit testing');

    /* ================================================================ 5. view, overlays, pixel grid, LOD, labels */
    const vw = await p.evaluate(async (ids) => {
      const R = HD.render, o = {};
      R.setView({x: 123.4, y: -56.7, zoom: 2.5});
      const w = R.screenToWorld(300, 200), s = R.worldToScreen(w[0], w[1]);
      o.round = [Math.abs(s[0] - 300) < 1e-6, Math.abs(s[1] - 200) < 1e-6]; o.origin = R.worldToScreen(0, 0); o.view = [R.view.x, R.view.y, R.view.zoom];
      let seen = null; const off = R.addOverlay((ctx, v) => { seen = [ctx.getTransform().a, v.zoom]; ctx.fillStyle = '#FF00FF'; ctx.fillRect(10, 10, 20, 20); });
      R.flush(); o.overlay = seen; o.overlayPx = T.px(20, 20);
      const frames = R.stats.frames; R.invalidate(); R.flush(); o.overlayMode = R.stats.mode; off(); R.flush(); o.overlayGone = T.px(20, 20);
      /* zoom to fit */
      R.zoomToFit(null, false); R.flush(); const b = R.exportBounds(HD.sel.page), a = R.worldToScreen(b.x, b.y), z = R.worldToScreen(b.x + b.w, b.y + b.h);
      o.fit = [a[0] >= 0, a[1] >= 0, z[0] <= R.size.w, z[1] <= R.size.h, R.view.zoom <= 1];
      R.zoomToFit([ids.star], false); R.flush(); const sb = HD.store.worldBounds(ids.star), sc = R.worldToScreen(sb.x + sb.w / 2, sb.y + sb.h / 2);
      o.fitSel = [Math.abs(sc[0] - R.size.w / 2) < 2, Math.abs(sc[1] - R.size.h / 2) < 2, R.view.zoom > 3]; o.star = T.px(sc[0], sc[1]);
      /* animated */
      R.setView({x: 0, y: 0, zoom: 1}, true); o.animStart = R.view.zoom !== 1; await new Promise(r => setTimeout(r, 420)); o.animEnd = [R.view.x, R.view.y, R.view.zoom];
      /* pixel grid above 800 % */
      R.setView({x: -20 * 16 + 8, y: -20 * 16 + 8, zoom: 16}); R.flush(); o.gridLine = T.px(8 + 16 * 5, 8 + 16 * 5 + 7); o.gridCell = T.px(8 + 16 * 5 + 7, 8 + 16 * 5 + 7);
      R.pixelGrid = false; R.flush(); o.gridOff = T.px(8 + 16 * 5, 8 + 16 * 5 + 7); R.pixelGrid = true;
      /* level of detail: far out, a node is a dot of its own colour; nothing is drawn for a speck */
      R.setView({x: 400, y: 300, zoom: 0.02}); R.flush(); o.lod = Object.assign({}, R.stats);
      const sp = R.worldToScreen(60, 50); o.lodPx = T.px(sp[0], sp[1]);
      R.setView({x: 0, y: 0, zoom: 1}); R.flush();
      return o;
    }, ids);
    assert.deepEqual(vw.round, [true, true]); assert.deepEqual(vw.origin, [vw.view[0], vw.view[1]], 'view.x / view.y is the screen place of world (0,0)'); assert.equal(vw.view[2], 2.5);
    assert.deepEqual(vw.overlay, [1, 2.5], 'overlays draw in screen space, scaled only by the device pixel ratio'); isColor(vw.overlayPx, [255, 0, 255], 'overlay'); assert.equal(vw.overlayMode, 'overlay', 'invalidate() alone never repaints the document');
    assert.ok(!near(vw.overlayGone, [255, 0, 255]), 'a removed overlay is gone');
    assert.deepEqual(vw.fit, [true, true, true, true, true]); assert.deepEqual(vw.fitSel, [true, true, true]); isColor(vw.star, [255, 177, 92], 'zoomed to the star');
    assert.ok(vw.animStart, 'an animated setView does not jump'); assert.deepEqual(vw.animEnd, [0, 0, 1]);
    assert.ok(!near(vw.gridLine, vw.gridCell, 3), 'pixel grid lines show above 800 %: ' + vw.gridLine + ' / ' + vw.gridCell); assert.ok(near(vw.gridOff, vw.gridCell, 3));
    assert.ok(vw.lod.flat > 20 && vw.lod.nodes < 12, 'far out, nodes are drawn as dots: ' + JSON.stringify(vw.lod)); assert.ok(!near(vw.lodPx, BG, 2), 'a dot is there');
    ok('view');

    /* ================================================================ 6. edits repaint only what changed, and never show stale pixels */
    const fresh = await p.evaluate(async (ids) => {
      const R = HD.render, S = HD.store, o = {};
      R.flush();
      /* a fill change deep in a (cached) frame */
      S.tx('c', () => S.set(S.children(ids.stripes)[0], {fills: [{type: 'solid', color: '#00FF00'}]})); R.flush(); o.modeEdit = R.stats.mode; o.kid = T.px(575, 150);
      /* a move: the old place is cleaned, the new place is painted */
      S.tx('m', () => S.set(ids.sIn, {x: 20, y: 640 - 20})); R.flush(); o.oldPlace = T.px(25, 50); o.newPlace = T.px(25, 650); o.modeMove = R.stats.mode;
      S.undo(); R.flush(); o.undone = T.px(25, 50);
      /* a component change repaints every instance of it */
      S.tx('comp', () => S.set(ids.compDot, {fills: [{type: 'solid', color: '#FF00FF'}]})); R.flush(); o.instBig = T.px(592, 574); o.instOverridden = T.px(716, 492);
      S.tx('ov', () => S.set(ids.inst, {ov: {}})); R.flush(); o.instPlain = T.px(716, 492);
      /* delete, hide, reorder */
      S.tx('del', () => S.remove([ids.blend])); R.flush(); o.deleted = T.px(250, 260);
      S.tx('hide', () => S.set(ids.blendBase, {visible: false})); R.flush(); o.hiddenNow = T.px(160, 230);
      S.tx('z', () => S.move([ids.grpA], ids.grp, null)); R.flush(); o.reordered = T.px(60, 250);
      /* the page colour */
      S.tx('bg', () => S.set(HD.sel.page, {bg: '#101010'})); R.flush(); o.bg = T.px(5, 5); S.undo(); R.flush(); o.bgBack = T.px(5, 5);
      /* a text being edited is hidden (the editor's own box shows it) */
      R.setEditing(ids.tBig); R.flush(); const b = S.worldBounds(ids.tBig); let dark = 0; for (let y = b.y; y < b.y + b.h; y += 2) for (let x = b.x; x < b.x + b.w; x += 2) { const q = T.px(x, y); if (q[0] < 100) dark++; } o.editingInk = dark;
      R.setEditing(null); R.flush(); dark = 0; for (let y = b.y; y < b.y + b.h; y += 2) for (let x = b.x; x < b.x + b.w; x += 2) { const q = T.px(x, y); if (q[0] < 100) dark++; } o.afterInk = dark;
      /* a name change needs no repaint at all */
      S.tx('n', () => S.set(ids.sCe, {name: 'Renamed'})); R.flush(); o.modeName = R.stats.mode;
      return o;
    }, ids);
    assert.equal(fresh.modeEdit, 'full', 'a page with a background blur repaints whole (what is behind the glass may have changed)'); isColor(fresh.kid, [0, 255, 0], 'a child changed inside a frame');
    isColor(fresh.oldPlace, BG, 'the old place is clean after a move'); isColor(fresh.newPlace, RED, 'the new place is painted'); isColor(fresh.undone, RED, 'undo paints it back');
    isColor(fresh.instBig, [255, 0, 255], 'instances follow their component'); isColor(fresh.instOverridden, [0, 255, 0], 'an override still wins'); isColor(fresh.instPlain, [255, 0, 255], 'dropping the override shows the component again');
    isColor(fresh.deleted, BG, 'a deleted node is gone'); isColor(fresh.hiddenNow, BG, 'a hidden node is gone'); isColor(fresh.reordered, [250, 122, 122], 'reordering repaints: red is on top now');
    isColor(fresh.bg, [16, 16, 16], 'page colour'); isColor(fresh.bgBack, BG, 'page colour back');
    assert.equal(fresh.editingInk, 0, 'the text being edited is not drawn'); assert.ok(fresh.afterInk > 20);
    assert.equal(fresh.modeName, 'overlay');
    ok('fresh pixels');

    /* random edits and pans, with and without the bitmap cache: the incremental picture must equal a full repaint */
    for (const noCache of [true, false]) {
      const r = await p.evaluate(async (noCache) => {
        const R = HD.render, S = HD.store;
        R.debug.noCache = noCache;
        T.mixed(600, false, 11);
        const pg = HD.sel.page, rnd = T.rng(5);
        S.tx('x', () => {
          const g = S.create('FRAME', pg, {x: 300, y: 120, w: 200, h: 160, rot: 15, opacity: 0.7, fills: [{type: 'solid', color: '#7C5CFF'}], effects: [{type: 'drop', x: 6, y: 10, blur: 16, color: '#000000', opacity: 0.4}]});
          S.create('TEXT', g, {x: 10, y: 10, chars: 'Rotated card', fontSize: 20, fills: [{type: 'solid', color: '#FFFFFF'}]});
          S.create('ELLIPSE', g, {x: 120, y: 80, w: 120, h: 120, fills: [{type: 'solid', color: '#FFB15C'}], blend: 'multiply'});
        });
        R.setView({x: 20, y: 10, zoom: 0.8}); R.flush();
        await new Promise(r => setTimeout(r, 320));
        const bad = [], modes = {};
        let blits = 0;
        for (let step = 0; step < 60; step++) {
          const k = Math.floor(rnd() * 9), ids = S.children(pg), id = ids[Math.floor(rnd() * Math.min(ids.length, 40))];
          const kids = S.children(id), kid = kids.length ? kids[Math.floor(rnd() * kids.length)] : id;
          let what = '';
          if (k === 0) { what = 'moveTop'; S.tx('m', () => S.set(id, {x: S.get(id).x + (rnd() * 80 - 40), y: S.get(id).y + (rnd() * 60 - 30)})); }
          else if (k === 1) { what = 'moveKid'; S.tx('m', () => S.set(kid, {x: (S.get(kid).x || 0) + (rnd() * 40 - 20)})); }
          else if (k === 2) { what = 'fill'; S.tx('m', () => S.set(kid, {fills: [{type: 'solid', color: T.COL[step % 10]}]})); }
          else if (k === 3) { what = 'pan'; const v = R.view; R.setView({x: v.x + Math.round(rnd() * 120 - 60), y: v.y + Math.round(rnd() * 90 - 45), zoom: v.zoom}); }
          else if (k === 4) { what = 'delete'; if (ids.length > 20) S.tx('m', () => S.remove([kid])); }
          else if (k === 5) { what = 'create'; S.tx('m', () => S.create('RECT', rnd() < 0.5 ? pg : id, {x: rnd() * 600, y: rnd() * 400, w: 50, h: 50, fills: [{type: 'solid', color: '#F87171'}], effects: rnd() < 0.5 ? [{type: 'drop', x: 2, y: 4, blur: 8, color: '#000000', opacity: 0.5}] : undefined})); }
          else if (k === 6) { what = 'rot+opacity'; S.tx('m', () => S.set(id, {rot: Math.round(rnd() * 40), opacity: 0.4 + rnd() * 0.6})); }
          else if (k === 7) { what = 'reorder'; S.tx('m', () => S.move([id], pg, ids[0])); }
          else { what = 'zoom'; const v = R.view, z = Math.max(0.5, Math.min(1.6, v.zoom * (rnd() < 0.5 ? 1.15 : 0.87))); R.setView({zoom: z, x: 450 - (450 - v.x) * z / v.zoom, y: 300 - (300 - v.y) * z / v.zoom}); }
          R.flush();
          modes[R.stats.mode] = (modes[R.stats.mode] || 0) + 1; blits += R.stats.blits;
          const a = T.snap();
          R.invalidate(true); R.flush();
          const d = T.diff(a, T.snap());
          if (d.big > 12 || d.small > 500) bad.push(step + ':' + what + ' ' + JSON.stringify(d));
          if (step % 9 === 8) await new Promise(r => setTimeout(r, 300));   /* let frames go cold so bitmaps get built */
        }
        /* at rest the picture is exact: the same as one painted with no cache at all */
        await new Promise(r => setTimeout(r, 500));
        R.flush(); const rest = T.snap();
        R.debug.noCache = true; R.invalidate(true); R.flush(); const exact = T.diff(rest, T.snap()); R.debug.noCache = false;
        return {bad, modes, blits, exact, cacheN: R.stats.cacheN};
      }, noCache);
      assert.deepEqual(r.bad, [], 'incremental painting (noCache=' + noCache + ') left stale pixels: ' + r.bad.join(' | '));
      assert.ok((r.modes.part || 0) > 15, 'most edits repaint only a part: ' + JSON.stringify(r.modes));
      assert.ok(r.exact.big <= 12 && r.exact.small <= 500, 'the picture at rest equals an uncached repaint: ' + JSON.stringify(r.exact));
      if (!noCache) assert.ok(r.blits > 0 && r.cacheN > 0, 'heavy frames are drawn from their bitmaps: ' + JSON.stringify(r));
      report['incremental_' + (noCache ? 'direct' : 'cached')] = r.modes;
    }
    /* a bitmap never outlives what it shows: change a layer while its frame is off screen, come back */
    const stale = await p.evaluate(async () => {
      const R = HD.render, S = HD.store, o = {};
      R.debug.noCache = false;
      T.mixed(300, false, 3);
      const pg = HD.sel.page, card = S.children(pg)[0], kid = S.children(card)[0];
      R.setView({x: 20, y: 20, zoom: 1}); R.flush();
      await new Promise(r => setTimeout(r, 330));
      R.invalidate(true); R.flush(); o.built = R.stats.built; R.invalidate(true); R.flush(); o.blits = R.stats.blits; o.nodes = R.stats.nodes; o.before = T.px(62, 52);
      R.setView({x: -3000, y: 20, zoom: 1}); R.flush();
      S.tx('c', () => S.set(kid, {fills: [{type: 'solid', color: '#00FF00'}]})); R.flush();
      R.setView({x: 20, y: 20, zoom: 1}); R.flush(); o.after = T.px(62, 52);
      await new Promise(r => setTimeout(r, 330)); R.invalidate(true); R.flush(); o.afterCold = T.px(62, 52);
      /* moving a cached frame keeps its bitmap: nothing is drawn again, it is only placed again */
      S.tx('m', () => S.set(card, {x: 30, y: 10})); R.flush(); o.moved = T.px(92, 42); o.movedOld = T.px(22, 180); o.moveStats = [R.stats.built, R.stats.blits > 0, R.stats.mode];
      /* opacity is applied when the bitmap is placed */
      S.tx('o', () => S.set(card, {opacity: 0.5})); R.flush(); o.half = T.px(92, 42); o.halfBuilt = R.stats.built;
      /* the cache keeps to its cap: least recently used bitmaps go */
      o.mbBefore = R.stats.cacheMB; R.cacheCapMB = 1; R.setView({x: 20, y: -900, zoom: 1}); R.flush(); await new Promise(r => setTimeout(r, 300)); R.invalidate(true); R.flush(); R.invalidate(true); R.flush();
      o.mbAfter = R.stats.cacheMB; o.stillRight = T.px(62 + 260, 52 + 900 - 800 + 0) ; R.cacheCapMB = 256;
      return o;
    });
    assert.ok(stale.built > 3 && stale.blits > 3 && stale.blits === stale.nodes, 'cold frames are drawn from bitmaps: ' + JSON.stringify(stale));
    isColor(stale.after, [0, 255, 0], 'a change made off screen is there when the frame comes back'); isColor(stale.afterCold, [0, 255, 0], 'and stays after the bitmap is made again');
    isColor(stale.moved, [0, 255, 0], 'a moved frame'); isColor(stale.movedOld, BG, 'left its old place'); assert.deepEqual(stale.moveStats, [0, true, 'part'], 'moving a frame reuses its bitmap');
    isColor(stale.half, [122, 250, 122], 'opacity on a cached frame'); assert.equal(stale.halfBuilt, 0);
    assert.ok(stale.mbBefore > 1.2 && stale.mbAfter <= 1.01, 'the bitmap cache keeps to its cap: ' + stale.mbBefore + ' MB -> ' + stale.mbAfter + ' MB');
    ok('incremental == full');

    /* styles, variables, nested instances */
    const sys = await p.evaluate(async () => {
      const R = HD.render, S = HD.store, pg = T.reset(), o = {}, solid = c => [{type: 'solid', color: c}];
      let a, b, c, d, t, cA, a1, cB, iA, iB, iB2;
      S.tx('sys', () => {
        S.set('0:0', {styles: {s1: {kind: 'fill', name: 'Brand', value: solid('#00FF00')}, s2: {kind: 'text', name: 'Title', value: {fontSize: 40, fontWeight: 700}}, s3: {kind: 'effect', name: 'Hard', value: [{type: 'drop', x: 12, y: 0, blur: 0, color: '#FF0000', opacity: 1}]}},
          vars: {v1: {name: 'ink', type: 'color', modes: {light: '#0000FF', dark: '#FFFF00'}}, v2: {name: 'fade', type: 'number', modes: {light: 0.5, dark: 1}}}, modes: ['light', 'dark']});
        a = S.create('RECT', pg, {x: 10, y: 10, w: 60, h: 60, fills: solid('#000000'), fillStyle: 's1'});
        b = S.create('RECT', pg, {x: 100, y: 10, w: 60, h: 60, fills: solid('#FF0000'), bind: {'fills.0.color': 'v1'}});
        c = S.create('RECT', pg, {x: 190, y: 10, w: 60, h: 60, fills: solid('#FFFFFF'), effectStyle: 's3'});
        d = S.create('RECT', pg, {x: 300, y: 10, w: 60, h: 60, fills: solid('#000000'), bind: {opacity: 'v2'}});
        t = S.create('TEXT', pg, {x: 10, y: 100, chars: 'Styled', textStyle: 's2', fills: solid('#000000')});
        cA = S.create('COMPONENT', pg, {x: 10, y: 200, w: 60, h: 60, name: 'A', fills: solid('#DDDDDD')}); a1 = S.create('RECT', cA, {x: 10, y: 10, w: 40, h: 40, fills: solid('#FF0000')});
        cB = S.create('COMPONENT', pg, {x: 100, y: 200, w: 140, h: 80, name: 'B', fills: solid('#FFFFFF')}); iA = S.create('INSTANCE', cB, {x: 10, y: 10, w: 60, h: 60, comp: cA, ov: {[a1]: {fills: solid('#00FF00')}}});
        iB = S.create('INSTANCE', pg, {x: 300, y: 200, w: 140, h: 80, comp: cB});
        iB2 = S.create('INSTANCE', pg, {x: 500, y: 200, w: 140, h: 80, comp: cB, ov: {[iA + '/' + a1]: {fills: solid('#0000FF')}, [iA]: {x: 70}}});
        S.create('INSTANCE', cA, {x: 0, y: 0, w: 10, h: 10, comp: cA});                 /* a component inside itself must not hang */
      });
      R.setView({x: 0, y: 0, zoom: 1}); R.flush();
      o.px = [T.px(40, 40), T.px(130, 40), T.px(256, 40), T.px(330, 40), T.px(40, 230), T.px(140, 240), T.px(340, 240), T.px(540, 240), T.px(600, 240)];
      o.textH = T.box(t)[3];
      S.tx('var', () => S.set('0:0', {modes: ['dark', 'light']})); R.flush(); o.dark = [T.px(130, 40), T.px(330, 40)];
      S.tx('style', () => S.set('0:0', {styles: Object.assign({}, S.get('0:0').styles, {s1: {kind: 'fill', name: 'Brand', value: solid('#FF00FF')}})})); R.flush(); o.restyled = T.px(40, 40);
      o.hit = [R.hitTest(540, 240, {deep: true}) === iB2, R.hitTest(600, 240, {deep: true}) === iB2, R.hitTest(660, 240, {deep: true}), R.hitTest(40, 230, {deep: true}) === a1];
      o.svg = new DOMParser().parseFromString(R.toSVG(pg), 'image/svg+xml').getElementsByTagName('parsererror').length;
      return o;
    });
    isColor(sys.px[0], [0, 255, 0], 'a fill style wins over the own fill'); isColor(sys.px[1], BLUE, 'a colour variable'); isColor(sys.px[2], RED, 'an effect style'); isColor(sys.px[3], [122, 122, 122], 'a number variable on opacity');
    isColor(sys.px[4], RED, 'component A'); isColor(sys.px[5], [0, 255, 0], 'an instance inside a component, with its override'); isColor(sys.px[6], [0, 255, 0], 'an instance of a component that holds an instance');
    isColor(sys.px[7], WHITE, 'the outer override moved the inner instance away'); isColor(sys.px[8], BLUE, 'an override through two levels: the outer instance wins');
    assert.equal(sys.textH, 48, 'a text style sets the size the text is measured with');
    isColor(sys.dark[0], [255, 255, 0], 'the other mode of a variable'); isColor(sys.dark[1], BLACK, 'number variable, other mode'); isColor(sys.restyled, [255, 0, 255], 'a changed style repaints its users');
    assert.deepEqual(sys.hit, [true, true, null, true]); assert.equal(sys.svg, 0);
    ok('styles, variables, nested instances');

    /* ================================================================ 7. export: canvas + SVG */
    const ex = await p.evaluate(async (ids) => {
      const R = HD.render, o = {};
      R.debug.noCache = false;
      T.gallery(); R.setView({x: 0, y: 0, zoom: 1}); R.flush(); await R.ready(HD.sel.page);
      const g = T.gallery.last = Object.assign({}, ids);
      const fresh = (function () { const S = HD.store, pg = HD.sel.page, m = {}; for (const id of S.children(pg)) m[S.get(id).name + '|' + S.get(id).x + '|' + S.get(id).y] = id; return m; })();
      const byPos = (x, y) => { const S = HD.store; for (const id of S.children(HD.sel.page)) { const n = S.get(id); if (n.x === x && n.y === y) return id; } return null; };
      const stripes = byPos(570, 110), soft = byPos(130, 120), rot = byPos(570, 230), drop = byPos(20, 120);
      const pxOf = (cv, x, y) => Array.from(cv.getContext('2d').getImageData(x, y, 1, 1).data);
      const c1 = R.toCanvas(stripes, 2); o.c1 = [c1.width, c1.height, pxOf(c1, 5, 80), pxOf(c1, 30, 80)];
      const c2 = R.toCanvas(soft, 3); o.c2 = [c2.width > 240, c2.height > 180, pxOf(c2, c2.width >> 1, c2.height >> 1), pxOf(c2, 1, 1)[3]];
      const c2b = R.toCanvas(soft, 3, {bounds: 'box'}); o.c2b = [c2b.width, c2b.height];
      const c3 = R.toCanvas(rot, 1, {bg: '#FFFFFF'}); o.c3 = [c3.width, c3.height, pxOf(c3, 2, 2), pxOf(c3, c3.width >> 1, c3.height >> 1)];
      const c4 = R.toCanvas(HD.sel.page, 0.5); o.c4 = [c4.width, c4.height, pxOf(c4, 2, 2)];
      const c5 = R.toCanvas(drop, 1); o.c5 = [c5.width, c5.height, pxOf(c5, 85, 65)];
      /* drawNode into any context */
      const dc = document.createElement('canvas'); dc.width = 200; dc.height = 120; const dx = dc.getContext('2d'); dx.translate(10, 10); dx.scale(2, 2); R.drawNode(dx, drop);
      o.draw = [pxOf(dc, 40, 40), pxOf(dc, 180, 135 > 119 ? 115 : 135), dx.getTransform().a];
      /* SVG */
      const svg = R.toSVG(HD.sel.page); o.svgLen = svg.length;
      const doc = new DOMParser().parseFromString(svg, 'image/svg+xml');
      o.svgErr = doc.getElementsByTagName('parsererror').length;
      const q = (s) => doc.querySelectorAll(s).length;
      o.svg = {rect: q('rect'), ellipse: q('ellipse'), path: q('path'), text: q('text'), tspan: q('tspan'), line: q('line'), lin: q('linearGradient'), rad: q('radialGradient'), clip: q('clipPath'), filter: q('filter'), mask: q('mask'), image: q('image'), script: q('script'), foreign: q('foreignObject')};
      o.svgDataImages = Array.from(doc.querySelectorAll('image')).every(im => /^data:image\/png;base64,/.test(im.getAttribute('href')));
      o.svgEscaped = svg.indexOf('&lt;b&gt;R&amp;D &quot;q&quot; &#39;s&#39;&lt;/b&gt;') >= 0 && svg.indexOf('<b>') < 0;
      o.svgXmlText = Array.from(doc.querySelectorAll('tspan')).some(t => t.textContent === '<b>R&D "q" \'s\'</b>');
      /* draw the SVG back and compare a few places with the canvas */
      const b = R.exportBounds(HD.sel.page);
      const im = new Image(); await new Promise((res, rej) => { im.onload = res; im.onerror = () => rej(new Error('the SVG does not load as a picture')); im.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg); });
      const sc = document.createElement('canvas'); sc.width = Math.ceil(b.w); sc.height = Math.ceil(b.h); sc.getContext('2d').drawImage(im, 0, 0);
      o.svgPx = [[25, 50], [60, 50], [235, 50], [200, 260], [30, 230], [60, 250], [610, 250], [810, 235], [770, 235], [40, 490], [100, 550], [716, 492], [700, 600], [686, 50], [104, 184], [243, 150]].map(pt => [pxOf(sc, Math.round(pt[0] - b.x), Math.round(pt[1] - b.y)).slice(0, 3), T.px(pt[0], pt[1])]);
      o.svgOne = R.toSVG(stripes).slice(0, 60);
      return o;
    }, ids);
    assert.deepEqual(ex.c1.slice(0, 2), [400, 160]); isColor(ex.c1[2].slice(0, 3), BLACK, 'export x2: stripe'); isColor(ex.c1[3].slice(0, 3), WHITE, 'export x2: gap');
    assert.deepEqual(ex.c2.slice(0, 2), [true, true], 'an export is as big as what is painted (the shadow too)'); isColor(ex.c2[2].slice(0, 3), [255, 177, 92], 'export x3'); assert.equal(ex.c2[3], 0, 'an export is transparent around the node');
    assert.deepEqual(ex.c2b, [240, 180]);
    assert.ok(ex.c3[0] > 85 && ex.c3[1] > 70, 'a turned node exports its turned bounds: ' + ex.c3.slice(0, 2)); isColor(ex.c3[2].slice(0, 3), WHITE, 'export bg'); isColor(ex.c3[3].slice(0, 3), [52, 211, 153], 'export of a turned node');
    isColor(ex.c4[2].slice(0, 3), BG, 'a page exports on its own colour'); assert.ok(ex.c4[0] > 400 && ex.c4[1] > 250);
    isColor(ex.c5[2].slice(0, 3), BLACK, 'export holds the shadow');
    isColor(ex.draw[0].slice(0, 3), WHITE, 'drawNode at the context origin, in its transform'); assert.equal(ex.draw[2], 2, 'drawNode leaves the context as it was');
    assert.equal(ex.svgErr, 0, 'the SVG is well-formed XML');
    assert.ok(ex.svg.rect > 20 && ex.svg.ellipse >= 5 && ex.svg.path >= 5 && ex.svg.text >= 10 && ex.svg.tspan >= 12 && ex.svg.line === 1 && ex.svg.lin >= 2 && ex.svg.rad >= 1 && ex.svg.clip >= 3 && ex.svg.filter >= 5 && ex.svg.mask >= 2 && ex.svg.image >= 3, 'real SVG elements: ' + JSON.stringify(ex.svg));
    assert.equal(ex.svg.script + ex.svg.foreign, 0); assert.ok(ex.svgDataImages, 'pictures are embedded as data URLs'); assert.ok(ex.svgEscaped && ex.svgXmlText, 'text is XML-escaped');
    assert.ok(ex.svgOne.startsWith('<svg xmlns="http://www.w3.org/2000/svg"'));
    const svgBad = ex.svgPx.filter(pr => !near(pr[0], pr[1], 40));
    assert.ok(svgBad.length === 0, 'the SVG draws like the canvas: ' + JSON.stringify(svgBad));
    ok('export');

    /* ================================================================ 8. pictures and fonts arrive later */
    const late = await p.evaluate(async () => {
      const R = HD.render, S = HD.store, pg = T.reset(), o = {};
      let r1, t1;
      S.tx('a', () => { r1 = S.create('RECT', pg, {x: 10, y: 10, w: 100, h: 100, fills: [{type: 'image', hash: 'lateimage01', mode: 'fill'}]}); t1 = S.create('TEXT', pg, {x: 10, y: 150, chars: 'Wide enough words', fontSize: 20, font: 'Test Family', fills: [{type: 'solid', color: '#000000'}]}); });
      R.setView({x: 0, y: 0, zoom: 1}); R.flush(); o.before = T.px(30, 30); o.imgNull = R.image('lateimage01') === null;
      await R.ready(pg); o.frames = R.stats.frames; await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      o.after = T.px(30, 30); const im = R.image('lateimage01'); o.img = !!im && /^blob:/.test(im.src) && im.naturalWidth === 64; o.bad = R.image('../../etc/passwd');
      /* a text sized before its font came is sized again when it comes - and only such texts */
      o.w0 = T.box(t1)[2];
      const real = CanvasRenderingContext2D.prototype.measureText;
      CanvasRenderingContext2D.prototype.measureText = function (s) { const m = real.call(this, s); if (/Test Family/.test(this.font)) { const w = m.width * 2; return {width: w, fontBoundingBoxAscent: m.fontBoundingBoxAscent, fontBoundingBoxDescent: m.fontBoundingBoxDescent, actualBoundingBoxAscent: m.actualBoundingBoxAscent, actualBoundingBoxDescent: m.actualBoundingBoxDescent}; } return m; };
      R.fontLoaded('Test Family'); await new Promise(r => setTimeout(r, 120));
      CanvasRenderingContext2D.prototype.measureText = real;
      o.w1 = T.box(t1)[2]; o.undo = S.undoLabel();
      return o;
    });
    isColor(late.before, [227, 227, 232], 'a picture that is still loading shows a grey box'); assert.ok(late.imgNull);
    isColor(late.after, RED, 'the picture is drawn when it arrives, without anyone asking'); assert.ok(late.img, 'image(hash) hands back an <img> (fetched with the Bearer token)'); assert.equal(late.bad, null);
    assert.ok(late.w1 > late.w0 * 1.7, 'the text is measured again with its real font: ' + late.w0 + ' -> ' + late.w1);
    ok('late resources');
    assert.deepEqual(A.errors, [], 'page errors: ' + A.errors.join('\n'));
    await p.close();

    /* ================================================================ 9. device pixel ratio 2: crisp, same geometry */
    const B = await open(700, 400, 2);
    const hi = await B.page.evaluate(async () => {
      const R = HD.render, S = HD.store, pg = T.reset(), o = {};
      S.tx('a', () => { S.create('RECT', pg, {x: 10, y: 10, w: 100, h: 60, fills: [{type: 'solid', color: '#FF0000'}]}); S.create('LINE', pg, {x: 10, y: 100.5, w: 100, strokes: [{type: 'solid', color: '#000000'}], strokeWeight: 1}); });
      R.setView({x: 0, y: 0, zoom: 1}); R.flush();
      const c = R.canvas, g = c.getContext('2d'), at = (x, y) => Array.from(g.getImageData(x, y, 1, 1).data).slice(0, 3);
      o.size = [c.width, c.height, R.dpr]; o.edge = [at(19, 40), at(20, 40), at(219, 40), at(220, 40)]; o.line = [at(60, 199), at(60, 200), at(60, 201), at(60, 202)];
      o.hit = [!!R.hitTest(50, 40, {deep: true}), R.hitTest(5, 5, {deep: true})]; o.w = R.screenToWorld(50, 40);
      let tr = null; const off = R.addOverlay((ctx) => { tr = ctx.getTransform().a; }); R.flush(); off(); o.overlayScale = tr;
      await B_resize();
      return o;
      function B_resize() { return Promise.resolve(); }
    });
    assert.deepEqual(hi.size, [1400, 800, 2]);
    isColor(hi.edge[0], BG, 'a box edge is one sharp device pixel (left, outside)', 2); isColor(hi.edge[1], RED, 'left, inside', 2); isColor(hi.edge[2], RED, 'right, inside', 2); isColor(hi.edge[3], BG, 'right, outside', 2);
    isColor(hi.line[0], BG, 'above a 1px line', 2); isColor(hi.line[1], BLACK, 'a 1px line is two crisp device pixels', 2); isColor(hi.line[2], BLACK, 'second row', 2); isColor(hi.line[3], BG, 'below it', 2);
    assert.deepEqual(hi.hit, [true, null]); assert.deepEqual(hi.w, [50, 40]); assert.equal(hi.overlayScale, 2);
    await B.page.setViewportSize({width: 500, height: 300});
    await B.page.waitForTimeout(200);
    const rs = await B.page.evaluate(() => { HD.render.flush(); const c = HD.render.canvas; return [c.width, c.height, T.px(50, 40)]; });
    assert.deepEqual(rs.slice(0, 2), [1000, 600], 'the canvas follows its box'); isColor(rs[2], RED, 'and is repainted after a resize');
    assert.deepEqual(B.errors, []);
    await B.page.close();
    ok('device pixel ratio');

    /* ================================================================ 10. speed */
    const P = await open(1280, 800, 1);
    const perf = await P.page.evaluate(async () => {
      const R = HD.render, out = {};
      const run = async (n, flat) => {
        const o = {nodes: T.mixed(n, flat, 7)};
        let t = performance.now(); R.zoomToFit(null, false); R.flush(); o.firstPaintAll = Math.round(performance.now() - t); o.fitZoom = Math.round(R.view.zoom * 1000) / 1000;
        await new Promise(r => setTimeout(r, 350));
        o.panZoomedOut = T.stat(T.pan(60, 7, 3));                                 /* everything on screen */
        R.debug.noBlit = true; o.repaintZoomedOut = T.stat(T.pan(12, 7, 3)); o.drawnZoomedOut = {nodes: R.stats.nodes, flat: R.stats.flat, blits: R.stats.blits}; R.debug.noBlit = false;
        const b = R.exportBounds(HD.sel.page);
        R.setView({zoom: 1, x: 640 - (b.x + b.w / 2), y: 400 - (b.y + b.h / 2)}); R.flush();
        await new Promise(r => setTimeout(r, 350));
        T.pan(10, 9, 5);
        o.pan100 = T.stat(T.pan(90, 9, 5));                                       /* 100 %: the usual working zoom */
        R.debug.noBlit = true; o.repaint100 = T.stat(T.pan(30, 9, 5)); R.debug.noBlit = false;
        /* drag one node that is on screen */
        const c0 = R.screenToWorld(440, 250), c1 = R.screenToWorld(840, 550);
        const hit = R.nodesInRect({x: c0[0], y: c0[1], w: c1[0] - c0[0], h: c1[1] - c0[1]}, HD.sel.page)[0];
        const ds = []; for (let i = 0; i < 40; i++) { const tt = performance.now(); HD.store.tx('drag', () => HD.store.set(hit, {x: (HD.store.get(hit).x || 0) + 2, y: (HD.store.get(hit).y || 0) + 1})); R.flush(); R.canvas.getContext('2d').getImageData(0, 0, 1, 1); ds.push(performance.now() - tt); }
        o.drag = T.stat(ds); o.dragMode = R.stats.mode;
        return o;
      };
      out.n5000_cards = await run(5000, false);
      out.n5000_flat = await run(5000, true);
      out.n20000_cards = await run(20000, false);
      out.n20000_flat = await run(20000, true);
      /* zooming a heavy page: the scaled preview keeps the frames short */
      R.zoomPreview = true; R.zoomToFit(null, false); R.flush(); await new Promise(r => setTimeout(r, 300));
      const zs = [], modes = {};
      for (let i = 0; i < 24; i++) { const v = R.view, z = v.zoom * 1.04, t = performance.now(); R.setView({zoom: z, x: 640 - (640 - v.x) * z / v.zoom, y: 400 - (400 - v.y) * z / v.zoom}); R.flush(); R.canvas.getContext('2d').getImageData(0, 0, 1, 1); zs.push(performance.now() - t); modes[R.stats.mode] = (modes[R.stats.mode] || 0) + 1; await new Promise(r => setTimeout(r, 8)); }
      out.zoom20000 = T.stat(zs); out.zoomModes = modes;
      await new Promise(r => setTimeout(r, 400)); out.settled = R.stats.mode;
      out.cacheMB = R.stats.cacheMB;
      return out;
    });
    report.perf = perf;
    /* generous limits (a shared CI box is slow); the real numbers are in the report */
    assert.ok(perf.n5000_cards.pan100.avg < 16 && perf.n5000_flat.pan100.avg < 16, '5,000 nodes: a pan frame at 100 % must stay under 16 ms: ' + JSON.stringify([perf.n5000_cards.pan100, perf.n5000_flat.pan100]));
    assert.ok(perf.n5000_cards.panZoomedOut.avg < 16 && perf.n5000_flat.panZoomedOut.avg < 16, '5,000 nodes all on screen: a pan frame must stay under 16 ms: ' + JSON.stringify([perf.n5000_cards.panZoomedOut, perf.n5000_flat.panZoomedOut]));
    assert.ok(perf.n20000_cards.panZoomedOut.avg < 33 && perf.n20000_flat.panZoomedOut.avg < 33, '20,000 nodes zoomed out: ' + JSON.stringify([perf.n20000_cards.panZoomedOut, perf.n20000_flat.panZoomedOut]));
    assert.ok(perf.n5000_cards.drag.avg < 16 && perf.n20000_flat.drag.avg < 33, 'dragging one node repaints a small part: ' + JSON.stringify([perf.n5000_cards.drag, perf.n20000_flat.drag]));
    assert.ok((perf.zoomModes.preview || 0) >= 10 && perf.settled !== 'preview', 'zooming a heavy page shows a scaled preview, then the real picture: ' + JSON.stringify(perf.zoomModes) + ' ' + perf.settled);
    assert.ok(perf.cacheMB <= 256, 'the bitmap cache keeps to its cap');
    assert.deepEqual(P.errors, []);
    await P.page.close();
    /* real frames (no read-backs on this page): is a pan 60 per second, and how long does the renderer itself work per frame? */
    const Q = await open(1280, 800, 1);
    const raf = await Q.page.evaluate(async () => {
      const R = HD.render, out = {};
      for (const [name, n, flat, zoom] of [['n5000_cards_100', 5000, false, 1], ['n5000_flat_100', 5000, true, 1], ['n5000_flat_all', 5000, true, 0], ['n20000_flat_all', 20000, true, 0]]) {
        T.mixed(n, flat, 7);
        R.zoomToFit(null, false);
        if (zoom) { const b = R.exportBounds(HD.sel.page); R.setView({zoom, x: 640 - (b.x + b.w / 2) * zoom, y: 400 - (b.y + b.h / 2) * zoom}); }
        R.flush();
        await new Promise(r => setTimeout(r, 400));
        const js = [], off = R.on('frame', s => js.push(s.ms));
        const gaps = await new Promise(res => { const g = []; let last = 0, k = 0; function step(ts) { if (last) g.push(ts - last); last = ts; if (k++ >= 120) return res(g); const v = R.view; R.setView({x: v.x - 9, y: v.y - 5, zoom: v.zoom}); requestAnimationFrame(step); } requestAnimationFrame(step); });
        off();
        out[name] = {frameGap: T.stat(gaps.slice(5)), over25ms: gaps.slice(5).filter(g => g > 25).length, rendererMs: T.stat(js.slice(5))};
      }
      return out;
    });
    report.perf.raf = raf;
    for (const k of Object.keys(raf)) assert.ok(raf[k].over25ms <= 12, k + ': a pan must run at the display rate (frames over 25 ms: ' + raf[k].over25ms + ' of 115) ' + JSON.stringify(raf[k]));
    assert.ok(raf.n5000_cards_100.rendererMs.avg < 16 && raf.n5000_flat_100.rendererMs.avg < 16 && raf.n5000_flat_all.rendererMs.avg < 16, '5,000 nodes: the renderer works under 16 ms a pan frame');
    assert.deepEqual(Q.errors, []);
    await Q.page.close();
    ok('speed');
  } finally {
    await browser.close();
    if (server) server.close();
  }
  console.log(JSON.stringify(report));
}

if (require.main === module) main().catch(e => { console.error(e && e.stack || e); process.exit(1); });
module.exports = {main};

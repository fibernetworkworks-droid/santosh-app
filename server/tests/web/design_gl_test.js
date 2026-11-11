/* HOOLA DESIGN D9a - the WebGL2 tile renderer (hd-render-gl.js) against the Canvas2D renderer (hd-render.js), in a REAL
   browser (headless Chromium: WebGL2 through SwiftShader, i.e. on the CPU). Serves the static design folder itself.
   1. pixels: a scripted page with every node type, paint and effect is drawn by BOTH renderers at several views
      (zoom 1, zoomed out with level of detail, zoomed in, a part-pixel pan, pixel ratio 2) and compared pixel by pixel;
      a page of plain shapes takes the GPU fast path and is compared the same way;
   2. edits + pans: the tiles follow every edit (no stale pixel) and a pan over made tiles paints nothing;
   3. the switch: 'hd.renderer' = 2d / gl / auto, and a lost WebGL context falls back to Canvas2D with no error;
   4. export + hit tests are the same code in both modes;
   5. speed: 5,000 / 20,000 / 100,000 mixed nodes at 1280x800 - load to first paint, pan and zoom frame times for both
      renderers, the pure composite cost, texture memory and tiles made a frame. Printed; asserted only where honest.
   Run:  node server/tests/web/design_gl_test.js     (DESIGN_SHOTS=<dir> writes PNGs to look at; GL_PERF=0 skips 5.)
   Exit 0 = pass, 1 = fail, 77 = could not run here. The last line is a JSON report. */
'use strict';
const http = require('http'), fs = require('fs'), path = require('path'), assert = require('node:assert/strict');
const DESIGN = path.resolve(__dirname, '../../app/static/console/design');
const SHOTS = process.env.DESIGN_SHOTS || '';
const FILES = ['hd-math.js', 'hd-core.js', 'hd-layout.js', 'hd-render.js', 'hd-render-gl.js'].concat(fs.existsSync(path.join(DESIGN, 'hd-index.js')) ? [] : []);

const IN_PAGE = `
window.T = {};
T.COL = ['#FF9A3C', '#C055F5', '#7C5CFF', '#2DD4BF', '#34D399', '#F87171', '#FFB15C', '#120E2A', '#3B82F6', '#EAB308'];
T.reset = function () {
  HD.store.load({nodes: {'0:0': {type: 'DOCUMENT'}, '0:1': {type: 'PAGE', parent: '0:0', idx: 'a', name: 'Page 1'}}}, 1);
  if (HD.sel.page !== '0:1') HD.sel.setPage('0:1');
  return '0:1';
};
T.rng = function (seed) { let s = seed >>> 0; return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; };
T.stat = function (a) { if (!a.length) return {avg: 0, p50: 0, p95: 0, max: 0, n: 0}; const s = a.slice().sort((x, y) => x - y), sum = a.reduce((x, y) => x + y, 0); const r = v => Math.round(v * 100) / 100; return {avg: r(sum / a.length), p50: r(s[s.length >> 1]), p95: r(s[Math.min(s.length - 1, Math.floor(s.length * 0.95))]), max: r(s[s.length - 1]), n: a.length}; };
/* the on-screen picture as an RGBA array, whichever renderer drew it */
T.pic = function () { const c = HD.render.snapshot(); return {w: c.width, h: c.height, d: c.getContext('2d').getImageData(0, 0, c.width, c.height).data}; };
T.diff = function (a, b) {
  let n8 = 0, n24 = 0, n100 = 0, max = 0, sum = 0;
  const bad = [];
  for (let i = 0; i < a.d.length; i += 4) {
    const d = Math.max(Math.abs(a.d[i] - b.d[i]), Math.abs(a.d[i + 1] - b.d[i + 1]), Math.abs(a.d[i + 2] - b.d[i + 2]));
    sum += d; if (d > max) max = d;
    if (d > 8) n8++; if (d > 24) n24++;
    if (d > 100) { n100++; if (bad.length < 12) { const p = i / 4; bad.push([p % a.w, Math.floor(p / a.w), [a.d[i], a.d[i + 1], a.d[i + 2]], [b.d[i], b.d[i + 1], b.d[i + 2]]]); } }
  }
  return {n8, n24, n100, max, mean: Math.round(sum / (a.d.length / 4) * 1000) / 1000, px: a.d.length / 4, bad};
};
T.gallery = function () {
  const S = HD.store, pg = T.reset(), ids = {};
  const solid = c => [{type: 'solid', color: c}];
  S.tx('gallery', () => {
    ids.sIn = S.create('RECT', pg, {x: 20, y: 20, w: 80, h: 60, fills: solid('#FFFFFF'), strokes: solid('#FF0000'), strokeWeight: 10, strokeAlign: 'inside'});
    ids.sCe = S.create('RECT', pg, {x: 130.5, y: 20.25, w: 80, h: 60, fills: solid('#FFFFFF'), strokes: solid('#FF0000'), strokeWeight: 10, strokeAlign: 'center'});
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
    S.create('RECT', ids.grp, {x: 0, y: 0, w: 60, h: 60, fills: solid('#FF0000')});
    S.create('RECT', ids.grp, {x: 30, y: 20, w: 60, h: 60, fills: solid('#0000FF')});
    ids.blendBase = S.create('RECT', pg, {x: 150, y: 220, w: 80, h: 80, fills: solid('#FFFF00')});
    ids.blend = S.create('RECT', pg, {x: 190, y: 240, w: 80, h: 40, fills: solid('#00FFFF'), blend: 'multiply'});
    ids.mgroup = S.create('GROUP', pg, {x: 300, y: 220});
    S.create('ELLIPSE', ids.mgroup, {x: 0, y: 0, w: 80, h: 80, fills: solid('#000000'), mask: true});
    S.create('RECT', ids.mgroup, {x: 0, y: 0, w: 80, h: 80, fills: [{type: 'linear', stops: [{pos: 0, color: '#FF0000'}, {pos: 1, color: '#0000FF'}], from: [0, 0], to: [1, 0]}]});
    ids.tmaskG = S.create('GROUP', pg, {x: 400, y: 220});
    S.create('TEXT', ids.tmaskG, {x: 0, y: 0, chars: 'MASK', fontSize: 40, fontWeight: 900, fills: solid('#000000'), mask: true});
    S.create('RECT', ids.tmaskG, {x: 0, y: 0, w: 140, h: 50, fills: solid('#FF0000')});
    ids.rot = S.create('RECT', pg, {x: 570, y: 230, w: 80, h: 40, rot: 30, fills: solid('#34D399'), strokes: solid('#120E2A'), strokeWeight: 2});
    ids.flip = S.create('VECTOR', pg, {x: 680, y: 220, w: 60, h: 60, flipH: true, path: 'M0 0 L60 30 L0 60 Z', fills: solid('#F87171')});
    ids.vec = S.create('VECTOR', pg, {x: 760, y: 220, w: 100, h: 30, path: 'M0 0 L50 0 L50 50 L0 50 Z M10 10 L10 40 L40 40 L40 10 Z', fillRule: 'evenodd', fills: solid('#7C5CFF')});
    ids.tCenter = S.create('TEXT', pg, {x: 20, y: 330, w: 200, autoResize: 'h', align: 'center', chars: 'Centered text that wraps on two lines', fontSize: 16, fills: solid('#120E2A')});
    ids.tRight = S.create('TEXT', pg, {x: 240, y: 330, w: 160, h: 70, autoResize: 'none', align: 'right', alignV: 'bottom', chars: 'Right bottom', fontSize: 16, fills: solid('#120E2A'), decoration: 'underline'});
    ids.tRuns = S.create('TEXT', pg, {x: 420, y: 330, chars: 'Plain BOLD red big', fontSize: 16, fills: solid('#120E2A'), runs: [{s: 6, e: 10, fontWeight: 800}, {s: 11, e: 14, fills: solid('#FF0000'), decoration: 'strike'}, {s: 15, e: 18, fontSize: 30}]});
    ids.tCase = S.create('TEXT', pg, {x: 420, y: 380, chars: 'upper case spaced', fontSize: 14, textCase: 'upper', letterSpacing: 4, fills: solid('#120E2A')});
    ids.tJust = S.create('TEXT', pg, {x: 640, y: 330, w: 180, autoResize: 'h', align: 'justify', lineHeight: 24, chars: 'Justified text spreads its words to both edges of the box nicely', fontSize: 14, fills: solid('#120E2A')});
    ids.tStroke = S.create('TEXT', pg, {x: 20, y: 400, chars: 'Outline', fontSize: 36, fontWeight: 800, fills: solid('#FFFFFF'), strokes: solid('#7C5CFF'), strokeWeight: 3, strokeAlign: 'outside'});
    ids.tGrad = S.create('TEXT', pg, {x: 200, y: 400, chars: 'Hxg', fontSize: 48, fills: [{type: 'radial', stops: [{pos: 0, color: '#FF0000'}, {pos: 1, color: '#0000FF'}], from: [0.5, 0.5], to: [1, 0.5]}]});
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
    ids.hollow = S.create('RECT', pg, {x: 900, y: 320, w: 80, h: 80, strokes: solid('#000000'), strokeWeight: 2});
    ids.line = S.create('LINE', pg, {x: 900, y: 460, w: 120, strokes: solid('#000000'), strokeWeight: 4, strokeCap: 'round'});
    ids.star = S.create('STAR', pg, {x: 1000, y: 320, w: 80, h: 80, sides: 5, ratio: 0.4, fills: solid('#FFB15C')});
    ids.clipF = S.create('FRAME', pg, {x: 900, y: 520, w: 100, h: 80, name: 'Clip', fills: solid('#FFFFFF')});
    S.create('RECT', ids.clipF, {x: 60, y: 20, w: 100, h: 40, fills: solid('#3B82F6')});
    ids.radial = S.create('ELLIPSE', pg, {x: 1040, y: 220, w: 60, h: 60, fills: [{type: 'radial', stops: [{pos: 0, color: '#FFFFFF'}, {pos: 1, color: '#FF0000'}], from: [0.5, 0.5], to: [1, 0.5]}]});
    ids.angular = S.create('RECT', pg, {x: 1040, y: 420, w: 60, h: 60, fills: [{type: 'angular', stops: [{pos: 0, color: '#FF0000'}, {pos: 0.5, color: '#0000FF'}, {pos: 1, color: '#FF0000'}], from: [0.5, 0.5], to: [1, 0.5]}]});
    ids.bool = S.create('GROUP', pg, {x: 1100, y: 520, w: 100, h: 80, bool: 'subtract', fills: solid('#2DD4BF')});
    S.create('RECT', ids.bool, {x: 0, y: 0, w: 100, h: 80});
    S.create('ELLIPSE', ids.bool, {x: 30, y: 20, w: 40, h: 40});
    ids.union = S.create('GROUP', pg, {x: 1100, y: 620, w: 120, h: 70, bool: 'union', fills: solid('#C055F5'), strokes: solid('#120E2A'), strokeWeight: 2});
    S.create('ELLIPSE', ids.union, {x: 0, y: 0, w: 70, h: 70});
    S.create('RECT', ids.union, {x: 50, y: 15, w: 70, h: 40, radius: 6});
    ids.big = S.create('FRAME', pg, {x: 20, y: 620, w: 1000, h: 300, name: 'Wide card', radius: 16, fills: [{type: 'linear', stops: [{pos: 0, color: '#FFD9A8'}, {pos: 0.5, color: '#FF9A3C'}, {pos: 1, color: '#C055F5'}], from: [0, 0], to: [1, 1]}],
      effects: [{type: 'drop', x: 0, y: 10, blur: 24, spread: 0, color: '#000000', opacity: 0.25}]});
    S.create('TEXT', ids.big, {x: 40, y: 40, chars: 'Diwali offer 50% off - \\u20B9 1,499', fontSize: 40, fontWeight: 700, fills: solid('#FFFFFF')});
    for (let i = 0; i < 12; i++) S.create(i % 2 ? 'ELLIPSE' : 'RECT', ids.big, {x: 40 + i * 78, y: 160, w: 60, h: 60, radius: 10, rot: i * 9, fills: solid(T.COL[i % 10]), opacity: i % 3 ? 1 : 0.6});
  });
  return ids;
};
/* only plain shapes: what the GPU fast path draws (solid rects, rounded rects, ellipses, opacity, rotation, frames that
   clip, groups), plus tiny ones for the level of detail */
T.shapes = function (n, seed) {
  const S = HD.store, pg = T.reset(), r = T.rng(seed || 7), C = T.COL;
  S.tx('shapes', () => {
    const f = S.create('FRAME', pg, {x: 10.5, y: 10.25, w: 300, h: 200, fills: [{type: 'solid', color: '#FFFFFF'}], name: 'Clip'});
    S.create('RECT', f, {x: 200, y: 40, w: 160, h: 60, fills: [{type: 'solid', color: '#3B82F6'}]});
    S.create('ELLIPSE', f, {x: -30, y: 120, w: 100, h: 100, fills: [{type: 'solid', color: '#F87171', opacity: 0.7}]});
    const g = S.create('GROUP', pg, {x: 340, y: 20});
    S.create('RECT', g, {x: 0, y: 0, w: 60, h: 60, radius: [20, 0, 10, 4], fills: [{type: 'solid', color: '#34D399'}]});
    S.create('RECT', g, {x: 40, y: 30, w: 60, h: 60, rot: 33, fills: [{type: 'solid', color: '#7C5CFF'}], opacity: 0.5});
    for (let i = 0; i < n; i++) {
      const k = i % 4, x = Math.round(r() * 1200 * 4) / 4, y = 230 + Math.round(r() * 520 * 4) / 4, w = 4 + r() * 90, h = 4 + r() * 70, c = C[i % 10];
      if (k === 0) S.create('RECT', pg, {x, y, w, h, fills: [{type: 'solid', color: c}]});
      else if (k === 1) S.create('RECT', pg, {x, y, w, h, radius: Math.min(w, h) * r() * 0.5, fills: [{type: 'solid', color: c}], opacity: 0.4 + r() * 0.6});
      else if (k === 2) S.create('ELLIPSE', pg, {x, y, w, h, fills: [{type: 'solid', color: c}], rot: r() * 90});
      else S.create('RECT', pg, {x, y, w: w * 0.2, h: h * 0.2, rot: r() * 45, fills: [{type: 'solid', color: c, opacity: 0.8}, {type: 'solid', color: '#FFFFFF', opacity: 0.2}]});
    }
  });
};
/* n mixed nodes (the render test's cards: a frame with rects, texts, ellipses, lines; every 4th with a shadow) */
T.mixed = function (n, seed) {
  const S = HD.store, pg = T.reset(), C = T.COL;
  const cols = Math.ceil(Math.sqrt(n / 10) * 1.3);
  let made = 0, i = 0;
  S.tx('gen', () => {
    while (made < n) {
      const cx = (i % cols) * 260, cy = Math.floor(i / cols) * 200; i++;
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
/* n flat nodes straight on the page, spread out (where the spatial grid matters most) */
T.flat = function (n) {
  const S = HD.store, pg = T.reset(), C = T.COL, cols = Math.ceil(Math.sqrt(n));
  S.tx('gen', () => {
    for (let m = 0; m < n; m++) {
      const cx = (m % cols) * 60, cy = Math.floor(m / cols) * 60, k = m % 5, c = C[m % 10];
      if (k === 0) S.create('RECT', pg, {x: cx, y: cy, w: 44, h: 40, fills: [{type: 'solid', color: c}], radius: m % 3 ? 0 : 8});
      else if (k === 1) S.create('ELLIPSE', pg, {x: cx, y: cy, w: 44, h: 40, fills: [{type: 'solid', color: c}], strokes: [{type: 'solid', color: '#120E2A'}], strokeWeight: 2});
      else if (k === 2) S.create('TEXT', pg, {x: cx, y: cy, chars: 'Label ' + m, fontSize: 12, fills: [{type: 'solid', color: '#120E2A'}]});
      else if (k === 3) S.create('STAR', pg, {x: cx, y: cy, w: 40, h: 40, fills: [{type: 'solid', color: c}], rot: (m * 7) % 360});
      else S.create('RECT', pg, {x: cx, y: cy, w: 44, h: 40, fills: [{type: 'linear', stops: [{pos: 0, color: c}, {pos: 1, color: '#FFFFFF'}]}], opacity: 0.8});
    }
  });
};
/* frame times: move the view, run one frame, wait for the GPU (or the 2D raster) to finish */
T.frames = function (frames, step) {
  const R = HD.render, out = [], made = [], comp = [];
  for (let i = 0; i < frames; i++) {
    const v = R.view, nv = step(v, i), t = performance.now();
    R.setView(nv); R.flush(); R.finish();
    out.push(performance.now() - t);
    if (R.stats.gl) { made.push(R.stats.gl.rendered); comp.push(R.stats.gl.composeMs); }
  }
  return {ms: T.stat(out), tiles: made.length ? T.stat(made) : null, composeMs: comp.length ? T.stat(comp) : null};
};
`;

function serve(png) {
  const server = http.createServer((req, res) => {
    const p = new URL(req.url, 'http://x').pathname;
    if (p === '/t.html') {
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'");
      return res.end('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;height:100%;overflow:hidden}#stage{position:relative;width:100%;height:100%}#c{position:absolute;inset:0;width:100%;height:100%}</style></head><body><div id="stage"><canvas id="c"></canvas></div>' +
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

async function main() {
  let chromium;
  try { ({chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright')); } catch (e) { console.log('SKIP: playwright is not installed'); process.exit(77); }
  const exe = process.env.HOOLA_CHROMIUM || process.env.CHROMIUM_EXECUTABLE || undefined;
  let browser;
  /* Chrome moves a 2D canvas between its GPU and CPU rasterisers on its own (a canvas that is read back often goes to the
     CPU), and the two anti-alias curves differently. So the pixel comparison runs with every 2D canvas on the CPU
     rasteriser (one rasteriser, so a difference is OURS); GL_ACCEL2D=1 runs it with Chrome's default instead. */
  const args = ['--no-sandbox', '--disable-dev-shm-usage', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'].concat(process.env.GL_ACCEL2D ? [] : ['--disable-accelerated-2d-canvas']);
  try { browser = await chromium.launch({executablePath: exe, headless: true, args}); }
  catch (e) { console.log('SKIP: Chromium can not start here: ' + String(e.message).split('\n')[0]); process.exit(77); }
  const report = {checks: 0, pixels: {}, perf: {}};
  const ok = (name) => { report.checks++; if (process.env.DESIGN_VERBOSE) console.log('ok  ' + name); };
  let server = null;
  try {
    const mk = await browser.newPage();
    const quad = Buffer.from(await mk.evaluate(() => { const c = document.createElement('canvas'); c.width = 64; c.height = 48; const x = c.getContext('2d'); x.fillStyle = '#FF0000'; x.fillRect(0, 0, 32, 24); x.fillStyle = '#00FF00'; x.fillRect(32, 0, 32, 24); x.fillStyle = '#0000FF'; x.fillRect(0, 24, 32, 24); x.fillStyle = '#FFFF00'; x.fillRect(32, 24, 32, 24); return c.toDataURL('image/png').split(',')[1]; }), 'base64');
    const hasGL = await mk.evaluate(() => !!document.createElement('canvas').getContext('webgl2'));
    await mk.close();
    if (!hasGL) { console.log('SKIP: no WebGL2 in this Chromium'); process.exit(77); }
    server = await serve(quad);
    const url = 'http://127.0.0.1:' + server.address().port + '/t.html';
    const open = async (mode, w, h, dpr) => {
      const page = await browser.newPage({viewport: {width: w || 1280, height: h || 800}, deviceScaleFactor: dpr || 1});
      const errors = [];
      page.on('pageerror', e => errors.push(String(e.stack || e.message)));
      page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push('console: ' + m.text()); });
      await page.addInitScript((mode) => { try { localStorage.setItem('hoola.console.token', 'fixture'); if (mode) localStorage.setItem('hd.renderer', mode); else localStorage.removeItem('hd.renderer'); sessionStorage.removeItem('hd.renderer.lost'); } catch (e) { /* no storage */ } }, mode);
      await page.goto(url);
      await page.evaluate(() => { HD.render.webFonts = false; HD.render.zoomPreview = false; HD.render.init(document.getElementById('c')); });
      return {page, errors};
    };
    const shot = async (page, name) => { if (SHOTS) { fs.mkdirSync(SHOTS, {recursive: true}); await page.screenshot({path: path.join(SHOTS, name + '.png')}); } };
    const pic = (page) => page.evaluate(() => { const p = T.pic(); return {w: p.w, h: p.h, d: Array.from(p.d)}; });
    /* a picture of where the two differ: red = more than 24 levels, orange = more than 8, grey = the Canvas2D picture */
    const diffShot = async (page, name, a, b) => {
      const m = new Uint8Array(a.d.length);
      for (let i = 0; i < a.d.length; i += 4) {
        const d = Math.max(Math.abs(a.d[i] - b.d[i]), Math.abs(a.d[i + 1] - b.d[i + 1]), Math.abs(a.d[i + 2] - b.d[i + 2])), gr = Math.round((b.d[i] + b.d[i + 1] + b.d[i + 2]) / 3 * 0.3 + 170);
        if (d > 24) { m[i] = 255; m[i + 1] = 0; m[i + 2] = 0; } else if (d > 8) { m[i] = 255; m[i + 1] = 150; m[i + 2] = 0; } else { m[i] = m[i + 1] = m[i + 2] = gr; }
        m[i + 3] = 255;
      }
      const b64 = await page.evaluate(([w, h, s]) => { const bin = atob(s), u = new Uint8ClampedArray(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); const c = document.createElement('canvas'); c.width = w; c.height = h; c.getContext('2d').putImageData(new ImageData(u, w, h), 0, 0); return c.toDataURL('image/png').split(',')[1]; }, [a.w, a.h, Buffer.from(m).toString('base64')]);
      fs.writeFileSync(path.join(SHOTS, name + '.png'), Buffer.from(b64, 'base64'));
    };
    const diffOf = (a, b) => {
      let n8 = 0, n24 = 0, n100 = 0, max = 0, sum = 0; const bad = [];
      for (let i = 0; i < a.d.length; i += 4) {
        const d = Math.max(Math.abs(a.d[i] - b.d[i]), Math.abs(a.d[i + 1] - b.d[i + 1]), Math.abs(a.d[i + 2] - b.d[i + 2]));
        sum += d; if (d > max) max = d; if (d > 8) n8++; if (d > 24) n24++;
        if (d > 100) { n100++; if (bad.length < 10) { const q = i / 4; bad.push([q % a.w, Math.floor(q / a.w), a.d.slice(i, i + 3), b.d.slice(i, i + 3)]); } }
      }
      return {n8, n24, n100, max, mean: Math.round(sum / (a.d.length / 4) * 1000) / 1000, px: a.d.length / 4, bad};
    };

    /* ================================================================ 1. the switch */
    {
      const A = await open('gl'), B = await open('2d'), C = await open(null);
      const st = async (P) => P.page.evaluate(() => ({r: HD.render.renderer, why: HD.render.rendererWhy, glCanvas: document.querySelectorAll('canvas.hd-canvas-gl').length}));
      const a = await st(A), b = await st(B), c = await st(C);
      assert.equal(a.r, 'gl', 'hd.renderer = gl draws with WebGL2: ' + JSON.stringify(a)); assert.equal(a.glCanvas, 1);
      assert.equal(b.r, '2d'); assert.equal(b.glCanvas, 0); assert.match(b.why, /2d/);
      /* auto: WebGL2 on a real GPU; this browser's WebGL2 is SwiftShader (the CPU), where Canvas2D is the faster one */
      report.auto = c;
      assert.ok(c.r === '2d' ? /software/i.test(c.why) : c.r === 'gl', 'auto: ' + JSON.stringify(c));
      for (const P of [A, B, C]) { assert.deepEqual(P.errors, []); await P.page.close(); }
      ok('switch');
    }

    /* ================================================================ 2. pixels: every node type, paint and effect */
    const views = [
      {name: 'z1', v: {x: 0, y: 0, zoom: 1}},
      {name: 'z1_part', v: {x: 37, y: -13, zoom: 1}},
      {name: 'z037', v: {x: 30, y: 20, zoom: 0.37}},
      {name: 'z0123', v: {x: 500, y: 300, zoom: 0.123}},
      {name: 'z25', v: {x: -900, y: -600, zoom: 2.5}},
      {name: 'z1_33', v: {x: -101, y: -77, zoom: 1.33}}
    ];
    const compare = async (gen, dpr, tag, limits) => {
      const G = await open('gl', 1280, 800, dpr), D = await open('2d', 1280, 800, dpr), out = {};
      for (const P of [G, D]) await P.page.evaluate(async ([gen, dbg]) => { Object.assign(HD.render.debug, dbg); if (dbg.margin && HD.renderGL) HD.renderGL.margin = dbg.margin; T[gen](300); HD.render.setView({x: 0, y: 0, zoom: 1}); HD.render.settle(); await HD.render.ready(HD.sel.page); await new Promise(r => setTimeout(r, 150)); HD.render.settle(); }, [gen, JSON.parse(process.env.GL_DEBUG || '{}')]);
      for (const vw of views) {
        const g = await G.page.evaluate((v) => { HD.render.setView(v); const t = HD.render.settle(); return {t, st: Object.assign({}, HD.render.stats.gl)}; }, vw.v);
        /* the Canvas2D picture at rest (its bitmaps are shown 1:1 only once nothing has moved for a moment) */
        await D.page.evaluate(async (v) => { HD.render.setView(v); HD.render.flush(); await new Promise(r => setTimeout(r, 330)); HD.render.invalidate(true); HD.render.flush(); }, vw.v);
        const ga = await pic(G.page), da = await pic(D.page), d = diffOf(ga, da);
        if (process.env.GL_PROBE) for (const q of JSON.parse(process.env.GL_PROBE)) { const i = (q[1] * ga.w + q[0]) * 4; console.log(vw.name, q, 'gl', ga.d.slice(i, i + 3), '2d', da.d.slice(i, i + 3)); }
        d.gpuTiles = g.st.gpuTiles; d.cpuTiles = g.st.cpuTiles;
        out[vw.name] = d;
        if (SHOTS) { await shot(G.page, tag + '_' + vw.name + '_gl'); await shot(D.page, tag + '_' + vw.name + '_2d'); await diffShot(D.page, tag + '_' + vw.name + '_diff', ga, da); }
        assert.ok(d.n100 <= limits.n100 && d.n24 <= limits.n24 * d.px, tag + ' ' + vw.name + ': GL and Canvas2D differ: ' + JSON.stringify(d));
      }
      for (const P of [G, D]) { assert.deepEqual(P.errors, [], tag + ' page errors'); await P.page.close(); }
      return out;
    };
    report.pixels.gallery = await compare('gallery', 1, 'gallery', {n100: 0, n24: 0.0005});
    report.pixels.gallery_dpr2 = await compare('gallery', 2, 'gallery2', {n100: 0, n24: 0.0005});
    ok('pixels: gallery');
    report.pixels.shapes = await compare('shapes', 1, 'shapes', {n100: 0, n24: 0.002});
    const gpuUsed = Object.values(report.pixels.shapes).reduce((s, d) => s + d.gpuTiles, 0);
    assert.ok(gpuUsed > 0, 'the plain-shape page takes the GPU fast path');
    ok('pixels: GPU fast path');

    console.log(JSON.stringify(report));
  } finally {
    if (server) server.close();
    await browser.close();
  }
}
main().catch(e => { console.error(e && e.stack || e); process.exit(1); });

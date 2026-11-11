/* HOOLA DESIGN - browser walk of phase D4 "hand-off" (hd-export.js) in the REAL editor, with the mock server of
   design_ui_test.js (REST + one-file WebSocket room + assets).
   Run:  node server/tests/web/design_export_test.js
         DESIGN_EXPORT_OUT=<dir>  keeps what was downloaded (the pytest wrapper opens the ZIP with zipfile and the PDF
                                  with pypdf);  DESIGN_SHOTS=<dir> also writes screenshots.
   Exit 0 = pass, 1 = fail, 77 = could not run here (no playwright / no Chromium). The last line is a JSON report.
   What is checked: PNG / JPG export sizes and pixel colours (a 1080 x 1080 frame at 1x IS 1080 x 1080 px), the refusal
   of a picture too big for a browser, the Export section and the Export dialog through their controls, the ZIP and PDF
   writers, Copy as PNG, an SVG export imported again (same geometry), a hostile SVG (nothing runs, nothing is fetched),
   a real-world style SVG (nested transforms, gradients, use / defs / symbol, style classes, clip, skew, text) compared
   number by number AND pixel by pixel with the browser's own picture of it, picture import (picker, drop, paste, one
   undo step), the Inspect tab with CSS / Flutter / Tailwind for an auto layout card - the CSS is put on real elements
   and compared with the canvas pixel by pixel - and Save a copy / Import a copy (.hoola.json). */
'use strict';
const fs = require('fs'), path = require('path'), os = require('os'), zlib = require('zlib'), assert = require('node:assert/strict');
const {startMock, newDoc, layoutProblems} = require('./design_ui_test.js');

const solid = (c, o) => ({type: 'solid', color: c, opacity: o === undefined ? 1 : o, visible: true});
function seed() {
  const doc = newDoc();
  Object.assign(doc.nodes, {
    '9:1': {type: 'FRAME', parent: '0:1', idx: 'a0', name: 'Post 1080', x: 0, y: 0, w: 1080, h: 1080, fills: [solid('#FF0000')], effects: [{type: 'drop', x: 0, y: 20, blur: 40, spread: 0, color: '#000000', opacity: 0.5, visible: true}]},
    '9:2': {type: 'RECT', parent: '9:1', idx: 'a0', name: 'Blue', x: 540, y: 540, w: 540, h: 540, fills: [solid('#0000FF')]},
    '9:3': {type: 'ELLIPSE', parent: '9:1', idx: 'a1', name: 'icons/Green dot', x: 100, y: 100, w: 200, h: 200, fills: [solid('#00FF00')], strokes: [solid('#000000')], strokeWeight: 4},
    '9:4': {type: 'FRAME', parent: '0:1', idx: 'a1', name: 'Story', x: 1200, y: 0, w: 540, h: 960, fills: [solid('#222244')]},
    '9:5': {type: 'FRAME', parent: '0:1', idx: 'a2', name: 'A4 पेज', x: 1800, y: 0, w: 595, h: 842, fills: [solid('#FFFFFF')]},
    '9:6': {type: 'TEXT', parent: '9:5', idx: 'a0', name: 'Head', x: 40, y: 40, chars: 'Invoice', fontSize: 40, fills: [solid('#111111')]}
  });
  return doc;
}
function pngBytes(w, h, rgb) {
  const raw = Buffer.alloc((w * 3 + 1) * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const o = y * (w * 3 + 1) + 1 + x * 3; raw[o] = rgb[0]; raw[o + 1] = rgb[1]; raw[o + 2] = rgb[2]; }
  const crcT = []; for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; crcT[n] = c >>> 0; }
  const crc = b => { let c = 0xFFFFFFFF; for (const v of b) c = crcT[(c ^ v) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
  const chunk = (t, d) => { const len = Buffer.alloc(4); len.writeUInt32BE(d.length); const td = Buffer.concat([Buffer.from(t, 'latin1'), d]), cr = Buffer.alloc(4); cr.writeUInt32BE(crc(td)); return Buffer.concat([len, td, cr]); };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2;
  return Buffer.concat([Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw)), chunk('IEND', Buffer.alloc(0))]);
}

const COMPLEX_SVG = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="640" height="480" viewBox="0 0 320 240">
  <title>Shop badge</title>
  <style>
    .card { fill: #FFFFFF; stroke: #223344; stroke-width: 2 }
    .accent { fill: url(#sun) }
    rect.soft { fill-opacity: .5 }
    #leaf { fill: #2E9E5B }
    .dash { stroke-dasharray: 6 3; stroke-linecap: round }
  </style>
  <defs>
    <linearGradient id="sun" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#FF8A00"/><stop offset="100%" stop-color="rgb(229,46,113)"/></linearGradient>
    <linearGradient id="sky" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="240"><stop offset="0" style="stop-color:#DDEEFF"/><stop offset="1" style="stop-color:#88AAEE;stop-opacity:.8"/></linearGradient>
    <radialGradient id="glow" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="white"/><stop offset="1" stop-color="navy"/></radialGradient>
    <linearGradient id="sun2" xlink:href="#sun" gradientTransform="rotate(90 .5 .5)"/>
    <g id="pip"><circle cx="0" cy="0" r="6" fill="tomato"/><rect x="-2" y="-12" width="4" height="8" fill="#333"/></g>
    <symbol id="badge" viewBox="0 0 20 20"><rect width="20" height="20" rx="4" fill="hsl(210, 80%, 40%)"/><path d="M4 10l4 4 8-8" fill="none" stroke="#fff" stroke-width="2.5"/></symbol>
    <clipPath id="win"><rect x="200" y="20" width="100" height="70"/></clipPath>
  </defs>
  <rect width="320" height="240" fill="url(#sky)"/>
  <g id="cards" transform="translate(20 20)">
    <rect class="card" width="120" height="80" rx="10"/>
    <g transform="translate(10 10) scale(2)">
      <rect class="accent soft" x="0" y="0" width="30" height="10"/>
      <circle cx="40" cy="15" r="8" fill="url(#glow)"/>
      <g transform="rotate(30)"><rect id="leaf" x="10" y="12" width="20" height="6"/></g>
    </g>
  </g>
  <ellipse cx="80" cy="170" rx="40" ry="20" fill="url(#sun2)" stroke="black" stroke-width="3" transform="rotate(-15 80 170)"/>
  <polygon points="170,120 200,180 140,180" fill="gold" stroke="#553300" stroke-linejoin="round" stroke-width="4" opacity=".8"/>
  <path d="M220 130 h60 a10 10 0 0 1 10 10 v30 q0 10 -10 10 h-60 z" fill="#7744CC" transform="skewX(-12)"/>
  <line class="dash" x1="20" y1="215" x2="300" y2="225" stroke="#AA0000" stroke-width="4"/>
  <use xlink:href="#pip" x="250" y="205"/>
  <use href="#pip" transform="translate(280 205) scale(1.5)"/>
  <use href="#badge" x="150" y="20" width="40" height="40"/>
  <g clip-path="url(#win)"><circle cx="250" cy="55" r="50" fill="#00AA88"/></g>
  <polyline points="20,120 40,105 60,120 80,105 100,120" fill="none" stroke="#005577" stroke-width="3"/>
  <text x="160" y="232" font-family="Inter, sans-serif" font-size="12" font-weight="bold" text-anchor="middle" fill="#112233">Shop <tspan fill="#CC0000">open</tspan></text>
  <rect x="5" y="5" width="20" height="20" style="display:none" fill="red"/>
</svg>`;

const HOSTILE_SVG = `<?xml version="1.0"?>
<!DOCTYPE svg [ <!ENTITY xxe SYSTEM "http://evil.invalid/xxe.txt"> ]>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="100" onload="window.__pwned = 'onload'">
  <script>window.__pwned = 'script';</script>
  <script xlink:href="http://evil.invalid/x.js"/>
  <style>@import url("http://evil.invalid/a.css"); rect { fill: url("http://evil.invalid/p.svg#g") red; background: url(http://evil.invalid/bg.png) }</style>
  <foreignObject width="100" height="100"><body xmlns="http://www.w3.org/1999/xhtml"><img src="http://evil.invalid/i.png" onerror="window.__pwned='img'"/><script>window.__pwned='fo'</script><iframe src="http://evil.invalid/f"></iframe></body></foreignObject>
  <a xlink:href="javascript:window.__pwned='href'"><rect id="ok" x="10" y="10" width="80" height="60" onclick="window.__pwned='click'" onmouseover="window.__pwned='over'"/></a>
  <image href="http://evil.invalid/track.png" x="0" y="0" width="50" height="50"/>
  <image xlink:href="//evil.invalid/track2.png" width="50" height="50"/>
  <image href="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIG9ubG9hZD0id2luZG93Ll9fcHduZWQ9MSIvPg==" width="20" height="20"/>
  <use href="http://evil.invalid/sprite.svg#icon" x="5" y="5"/>
  <circle cx="150" cy="50" r="30" fill="url(http://evil.invalid/grad.svg#g)" style="filter:url(http://evil.invalid/f.svg#f)"/>
  <text x="10" y="95" font-family="EvilFont, Comic Sans MS">hi &xxe;</text>
  <animate attributeName="x" to="100" onbegin="window.__pwned='anim'"/>
  <set attributeName="onclick" to="window.__pwned='set'"/>
</svg>`;

async function main() {
  let chromium;
  try { ({chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright')); } catch (e) { console.log('SKIP: playwright is not installed'); process.exit(77); }
  const outDir = process.env.DESIGN_EXPORT_OUT || fs.mkdtempSync(path.join(os.tmpdir(), 'hd-export-'));
  fs.mkdirSync(outDir, {recursive: true});
  const shots = process.env.DESIGN_SHOTS || ''; if (shots) fs.mkdirSync(shots, {recursive: true});
  let browser;
  try { browser = await chromium.launch({executablePath: process.env.CHROMIUM_EXECUTABLE || undefined, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage']}); }
  catch (e) { console.log('SKIP: Chromium can not start here: ' + String(e.message).split('\n')[0]); process.exit(77); }
  const mock = await startMock(seed());
  const origin = 'http://127.0.0.1:' + mock.port, base = origin + '/console/design';
  const errors = [], requests = [], report = {checks: 0, out: outDir, files: {}};
  const ok = (cond, msg) => { assert.ok(cond, msg); report.checks++; };
  const eq = (a, b, msg) => { assert.deepEqual(a, b, msg); report.checks++; };
  const near = (a, b, tol, msg) => { assert.ok(Math.abs(a - b) <= tol, (msg || '') + ': ' + a + ' is not ' + b + ' (+-' + tol + ')'); report.checks++; };
  async function newPage(ctxOpts) {
    const ctx = await browser.newContext(Object.assign({viewport: {width: 1440, height: 900}, acceptDownloads: true, colorScheme: 'light'}, ctxOpts));
    await ctx.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: origin}).catch(() => {});
    const page = await ctx.newPage();
    page.on('pageerror', e => errors.push(e.message + ' ' + String(e.stack || '').split('\n').slice(1, 3).join(' ')));
    page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|net::ERR/.test(m.text())) errors.push('console: ' + m.text()); });
    page.on('request', r => requests.push(r.url()));
    await page.route(/^https:\/\/fonts\.(googleapis|gstatic)\.com\//, r => r.fulfill({contentType: 'text/css', body: ''}));
    await page.addInitScript(() => localStorage.setItem('hoola.console.token', 'fixture-only'));
    return page;
  }
  const mounted = page => page.waitForFunction(() => window.HD && HD.ui && HD.ui.mounted && HD.net.status === 'live' && HD.store.pages().length > 0, null, {timeout: 20000});
  const shot = async (page, name) => { if (shots) await page.screenshot({path: path.join(shots, name + '.png')}); };
  const save = async (dl, as) => { const p = path.join(outDir, as); await dl.saveAs(p); report.files[as] = {name: dl.suggestedFilename(), path: p, size: fs.statSync(p).size}; return p; };
  /* the shared layout check does not know about a scrolled panel: a control scrolled away above it is not "outside the window" */
  const layout = async page => { const scrolled = await page.evaluate(() => Array.from(document.querySelectorAll('.hd-pbody')).some(el => el.scrollTop > 0)); const all = await page.evaluate(layoutProblems); return all.filter(l => !(scrolled && /^outside the window: /.test(l))); };
  const t00 = Date.now(), step = name => { if (process.env.DESIGN_TRACE) console.error('[' + ((Date.now() - t00) / 1000).toFixed(1) + 's] ' + name); };
  const toastOf = page => page.evaluate(() => { const t = document.querySelector('.hd-toast'); return t ? t.textContent : ''; });
  try {
    const page = await newPage();
    await page.goto(base + '#/f/f1'); await mounted(page); await page.waitForTimeout(300);

    /* ---- it plugged in, and the editor's own commands are still there ---- */
    step("it plugged in, and the editor's own commands are still there");
    const wired = await page.evaluate(() => ({hooks: ['export', 'exportSection', 'importSvg'].every(k => typeof HD.ui.hooks[k] === 'function'), panel: HD.ui.state.panels.right.some(p => p.id === 'inspect'), api: typeof HD.handoff.renderOne,
      own: HD.ui.run('selectAll')}));
    ok(wired.hooks && wired.panel && wired.api === 'function', 'the hooks, the Inspect panel and HD.handoff are there'); ok(wired.own === true, 'the editor\u2019s own commands were not lost');
    await page.locator('canvas.hd-canvas').focus(); await page.keyboard.press('Control+K'); await page.waitForSelector('.hd-palq');
    for (const q of ['Copy as PNG', 'Copy as Flutter', 'Place an image', 'hoola.json', 'Undo', 'Zoom to fit']) { await page.locator('.hd-palq').fill(q); await page.waitForTimeout(40); ok(await page.locator('.hd-pallist .hd-mi').count() >= 1, 'the command palette knows \u201C' + q + '\u201D'); }
    await page.keyboard.press('Escape'); await page.evaluate(() => { HD.sel.set(['9:1']); }); await page.waitForTimeout(250);

    /* ---- the writers: CRC32, file names, sizes ---- */
    step('the writers: CRC32, file names, sizes');
    const unit = await page.evaluate(() => { const H = HD.handoff;
      return {crc: H.crc32(new TextEncoder().encode('123456789')), names: ['icons/home', '../../etc/passwd', 'CON', '  a<b>:c?*.png  ', '', 'पोस्टर 1'].map(n => [H.safeName(n, false), H.safeName(n, true)]),
        sizes: ['2x', '0.5', '512w', '300 h', '3,5x', 'abc', '0x', '99x', '1080W'].map(s => H.parseSize(s)), colors: ['#abc', 'rgb(255 0 0 / 50%)', 'hsl(120, 100%, 25%)', 'rebeccapurple', 'none', 'url(http://x/y)', 'transparent'].map(c => H.parseColor(c)),
        tf: H.parseTransform('translate(10 20) rotate(90) scale(2)').map(v => Math.round(v * 1000) / 1000), dec: H.decomp([-1, 0, 0, 1, 0, 0]), path: H.parsePathD('M10 10h20a5 5 0 01.5.5zm1 1').map(s => s[0]).join('')}; });
    eq(unit.crc, 0xCBF43926, 'CRC32 of the check string');
    eq(unit.names, [['icons-home', 'icons/home'], ['etc-passwd', 'etc/passwd'], ['_CON', '_CON'], ['a-b-c-.png', 'a-b-c-.png'], ['layer', 'layer'], ['पोस्टर 1', 'पोस्टर 1']], 'layer names made safe as file names');
    eq(unit.sizes, [{scale: 2}, {scale: 0.5}, {scale: 1, w: 512}, {scale: 1, h: 300}, {scale: 3.5}, null, null, {scale: 8}, {scale: 1, w: 1080}], 'size words');
    eq(unit.colors, [{hex: '#AABBCC', a: 1}, {hex: '#FF0000', a: 0.5}, {hex: '#008000', a: 1}, {hex: '#663399', a: 1}, null, null, {hex: '#000000', a: 0}], 'colours');
    eq(unit.tf, [0, 2, -2, 0, 10, 20], 'a transform list'); ok(unit.dec.flipH && !unit.dec.flipV && unit.dec.rot === 0 && unit.dec.ok, 'a mirror is a flip, not a half turn'); eq(unit.path, 'MLCZM', 'path data with packed arc flags');

    /* ---- PNG / JPG: exact sizes, real colours, the limit ---- */
    step('PNG / JPG: exact sizes, real colours, the limit');
    const ex = await page.evaluate(async () => {
      const H = HD.handoff, o = {};
      const pixels = async (blob, pts) => { const bm = await createImageBitmap(blob), cv = document.createElement('canvas'); cv.width = bm.width; cv.height = bm.height; const c = cv.getContext('2d'); c.drawImage(bm, 0, 0); return pts.map(p => Array.from(c.getImageData(p[0], p[1], 1, 1).data)); };
      const a = await H.renderOne('9:1', {fmt: 'png', scale: 1}); o.one = [a.w, a.h, a.blob.type]; o.px = await pixels(a.blob, [[10, 10], [800, 800], [200, 200], [1079, 1079], [0, 0]]);
      const head = new DataView(await a.blob.slice(0, 24).arrayBuffer()); o.pngHead = [head.getUint32(16), head.getUint32(20)];
      const b2 = await H.renderOne('9:1', {fmt: 'png', scale: 2}); o.two = [b2.w, b2.h];
      const w = await H.renderOne('9:1', {fmt: 'jpg', scale: 1, w: 512}); o.jpg = [w.w, w.h, w.blob.type];
      const hh = await H.renderOne('9:4', {fmt: 'png', scale: 1, h: 480}); o.fixedH = [hh.w, hh.h];
      const outer = await H.renderOne('9:1', {fmt: 'png', scale: 1}, {outer: true}); o.outer = [outer.w, outer.h];
      const dot = await H.renderOne('9:3', {fmt: 'png', scale: 1}); o.dot = [dot.w, dot.h]; o.dotPx = await pixels(dot.blob, [[0, 0], [102, 102]]);
      const dj = await H.renderOne('9:3', {fmt: 'jpg', scale: 1}); o.dotJpg = (await pixels(dj.blob, [[1, 1], [102, 102]]));
      try { const big = await H.renderOne('9:4', {fmt: 'png', scale: 4}); o.max = [big.w, big.h]; } catch (e) { o.max = e.message; }
      try { await H.renderOne('9:1', {fmt: 'png', scale: 1, w: 16384}); o.big = 'made'; } catch (e) { o.big = e.message; o.bigFlag = e.tooBig; o.bigMax = e.max; }
      o.plan = H.plan([{id: '9:1', row: {fmt: 'png', scale: 1}}, {id: '9:3', row: {fmt: 'png', scale: 2, suffix: '@2x'}}, {id: '9:3', row: {fmt: 'png', scale: 2, suffix: '@2x'}}, {id: '9:1', row: {fmt: 'png', scale: 8}}, {id: '9:5', row: {fmt: 'pdf'}}]).map(p => [p.name, p.w, p.h, p.unit, p.tooBig]);
      return o;
    });
    eq(ex.one, [1080, 1080, 'image/png'], 'a 1080 x 1080 frame at 1x is 1080 x 1080 px (its shadow does not grow it)'); eq(ex.pngHead, [1080, 1080], 'and the PNG file says so');
    eq(ex.px, [[255, 0, 0, 255], [0, 0, 255, 255], [0, 255, 0, 255], [0, 0, 255, 255], [255, 0, 0, 255]], 'the colours of the frame');
    eq(ex.two, [2160, 2160], '2x'); eq(ex.jpg, [512, 512, 'image/jpeg'], 'a fixed width'); eq(ex.fixedH, [270, 480], 'a fixed height keeps the proportions');
    ok(ex.outer[0] > 1080 && ex.outer[1] > 1080, 'asked for, the shadow outside the frame is kept: ' + ex.outer);
    eq(ex.dot, [204, 204], 'a shape is exported with its stroke'); eq(ex.dotPx[0][3], 0, 'PNG: transparent around the shape'); eq(ex.dotPx[1].slice(0, 3), [0, 255, 0], 'the dot');
    ok(ex.dotJpg[0][0] > 245 && ex.dotJpg[0][1] > 245 && ex.dotJpg[0][2] > 245, 'JPG: white where the PNG is transparent ' + ex.dotJpg[0]); ok(ex.dotJpg[1][1] > 240 && ex.dotJpg[1][0] < 20, 'JPG keeps the colour');
    eq(ex.max, [2160, 3840], 'a big picture that fits is made at full size'); ok(/more than a browser can draw/.test(ex.big) && /largest size that works is/.test(ex.big) && ex.bigFlag === true && ex.bigMax > 8 && ex.bigMax < 12, 'too big is refused with the size that works: ' + ex.big);
    eq(ex.plan, [['Post 1080.png', 1080, 1080, 'px', false], ['icons/Green dot@2x.png', 408, 408, 'px', false], ['icons/Green dot@2x-2.png', 408, 408, 'px', false], ['Post 1080-2.png', 8640, 8640, 'px', false], ['A4 पेज.pdf', 595, 842, 'pt', false]], 'the plan: names, sizes, no two files alike');

    /* ---- the Export section of the Design panel ---- */
    step('the Export section of the Design panel');
    const sec = page.locator('.hd-right section[aria-label="Export"]');
    await sec.scrollIntoViewIfNeeded(); ok(await sec.locator('.hdx-go').isVisible(), 'the Export button is in the Design panel');
    await sec.locator('.hdx-add').click(); await sec.locator('.hdx-add').click(); await page.waitForTimeout(150);
    eq(await page.evaluate(() => HD.store.get('9:1').exports), [{fmt: 'png', scale: 1, suffix: ''}, {fmt: 'png', scale: 2, suffix: '@2x'}], 'two export rows were written to the node');
    const row2 = sec.locator('.hdx-row').nth(1);
    await row2.locator('.hdx-size input').fill('512w'); await row2.locator('.hdx-size input').press('Enter'); await row2.locator('.hdx-fmt').selectOption('jpg');
    await sec.locator('.hdx-row').nth(1).locator('.hdx-suffix').fill('-small'); await sec.locator('.hdx-row').nth(1).locator('.hdx-suffix').press('Enter'); await page.waitForTimeout(150);
    eq(await page.evaluate(() => HD.store.get('9:1').exports), [{fmt: 'png', scale: 1, suffix: ''}, {fmt: 'jpg', scale: 1, suffix: '-small', w: 512}], 'size, format and suffix edited in the panel');
    await page.waitForFunction(() => { const c = document.querySelector('.hdx-prevcv'); return c && c.width > 10; }, null, {timeout: 5000}); ok(/1,080 × 1,080 px/.test(await sec.locator('.hdx-cap').textContent()), 'the preview says the size');
    eq(await layout(page), [], 'layout with the Export section, light'); await shot(page, 'export-section');
    let [dl] = await Promise.all([page.waitForEvent('download'), sec.locator('.hdx-go').click()]);
    eq(dl.suggestedFilename(), 'Post 1080.zip', 'two files of one layer leave as one ZIP'); await save(dl, 'section.zip');
    await page.evaluate(() => HD.store.undo()); await page.waitForTimeout(150);
    eq(await page.evaluate(() => HD.store.get('9:1').exports[1].suffix), '@2x', 'an export setting is an ordinary edit: undo takes the last one back');
    await page.evaluate(() => { HD.store.tx('rows', () => HD.store.set('9:1', {exports: [{fmt: 'png', scale: 1, suffix: ''}, {fmt: 'jpg', scale: 1, suffix: '-small', w: 512}]})); }); await page.waitForTimeout(200);

    /* ---- the Export dialog: selection, all frames, the list of what will be made, one PDF ---- */
    step('the Export dialog: selection, all frames, the list of what w');
    await page.locator('.hd-top button[title^="Export"]').click(); await page.waitForSelector('.hdx-dialog');
    eq(await page.locator('.hdx-dialog .hdx-item .hdx-iname').allTextContents(), ['Post 1080.png', 'Post 1080-small.jpg'], 'the dialog lists the selection’s own exports');
    await page.locator('.hdx-dialog .hdx-scope button').nth(1).click();
    eq(await page.locator('.hdx-dialog .hdx-item .hdx-iname').allTextContents(), ['Post 1080.png', 'Post 1080-small.jpg', 'Story.png', 'A4 पेज.png'], 'all frames of the page');
    ok(/4 files, packed in Shop poster\.zip/.test(await page.locator('.hdx-sum').textContent()), 'it says a ZIP will be made');
    await page.locator('.hdx-dialog .hdx-size input').fill('40x'); await page.locator('.hdx-dialog .hdx-size input').press('Enter');           /* clamped to 8x: Story 4320 x 7680 fits, nothing is too big yet */
    await page.locator('.hdx-dialog .hdx-opts input[type=checkbox]').first().uncheck();                                                        /* not the layers' own rows: every frame at 8x */
    await page.waitForTimeout(100);
    eq(await page.locator('.hdx-dialog .hdx-item.bad').count(), 0, '8x of these frames still fits');
    await page.evaluate(() => { HD.store.tx('big', () => HD.store.set('9:4', {w: 5400, h: 9600})); }); await page.locator('.hdx-dialog .hdx-size input').fill('4x'); await page.locator('.hdx-dialog .hdx-size input').press('Enter'); await page.waitForTimeout(100);
    eq(await page.locator('.hdx-dialog .hdx-item.bad').count(), 1, 'a 21,600 x 38,400 px picture is marked too large'); ok(await page.locator('.hdx-foot .hd-btn.pri').isDisabled(), 'and Export waits');
    ok(/larger than a browser can draw/.test(await page.locator('.hdx-dnote').textContent()), 'with the reason'); await shot(page, 'export-dialog-too-big');
    await page.locator('.hdx-dialog .hdx-item.bad .hd-linkbtn').click(); await page.waitForTimeout(100);
    eq(await page.locator('.hdx-dialog .hdx-item.bad').count(), 0, 'one tap takes the largest size that works'); ok(await page.locator('.hdx-foot .hd-btn.pri').isEnabled(), 'then it can go');
    await page.evaluate(() => { HD.store.undo(); }); await page.locator('.hdx-dialog .hdx-size input').fill('1x'); await page.locator('.hdx-dialog .hdx-size input').press('Enter');
    await page.locator('.hdx-dialog .hdx-fmt').selectOption('pdf'); await page.waitForTimeout(100);
    ok(/1 PDF with 3 pages/.test(await page.locator('.hdx-sum').textContent()), 'PDF: one file, a page for each frame'); ok(/can not be selected/.test(await page.locator('.hdx-dnote').textContent()), 'it says plainly that the pages are pictures');
    await page.evaluate(() => { for (const el of document.querySelectorAll('.hd-pbody')) el.scrollTop = 0; });
    eq(await layout(page), [], 'layout with the Export dialog'); await shot(page, 'export-dialog');
    [dl] = await Promise.all([page.waitForEvent('download'), page.locator('.hdx-foot .hd-btn.pri').click()]);
    eq(dl.suggestedFilename(), 'Shop poster.pdf'); await save(dl, 'frames.pdf'); await page.waitForSelector('.hdx-dialog', {state: 'detached'});
    /* the ZIP writer with a Devanagari name and a folder; one SVG file straight from the engine */
    const zipB64 = await page.evaluate(async () => { const H = HD.handoff, enc = new TextEncoder(); const blob = H.zip([{name: 'पोस्टर/नमस्ते.txt', data: enc.encode('namaste नमस्ते')}, {name: 'a b.bin', data: new Uint8Array([0, 255, 1, 254])}, {name: 'empty.txt', data: new Uint8Array(0)}]);
      const u = new Uint8Array(await blob.arrayBuffer()); let s = ''; for (const c of u) s += String.fromCharCode(c); return btoa(s); });
    fs.writeFileSync(path.join(outDir, 'unit.zip'), Buffer.from(zipB64, 'base64')); report.files['unit.zip'] = {path: path.join(outDir, 'unit.zip')};

    /* ---- Copy as PNG (Ctrl+Shift+C) and Copy as code in the right-click menu ---- */
    step('Copy as PNG (Ctrl+Shift+C) and Copy as code in the right-cli');
    await page.evaluate(() => HD.sel.set(['9:3'])); await page.locator('canvas.hd-canvas').focus(); await page.keyboard.press('Control+Shift+C');
    await page.waitForFunction(() => /Copied as PNG/.test((document.querySelector('.hd-toast') || {}).textContent || ''), null, {timeout: 8000});
    const clip = await page.evaluate(async () => { try { const items = await navigator.clipboard.read(), bl = await items[0].getType('image/png'), bm = await createImageBitmap(bl); return [bm.width, bm.height]; } catch (e) { return String(e); } });
    eq(clip, [408, 408], 'the clipboard holds the layer as a PNG at 2x');
    const sp = await page.evaluate(() => { const s = HD.render.worldToScreen(200, 200), r = HD.tools.canvas.getBoundingClientRect(); return [r.left + s[0], r.top + s[1]]; });
    await page.mouse.click(sp[0], sp[1], {button: 'right'}); await page.waitForSelector('.hd-menu');
    const menu = await page.locator('.hd-menu .hd-mlab').allTextContents(); ok(['Copy as PNG', 'Copy as SVG', 'Copy as code'].every(l => menu.includes(l)), 'the menu has Copy as PNG / SVG / code: ' + menu.join(', '));
    await page.locator('.hd-menu .hd-mi', {hasText: 'Copy as code'}).click(); await page.locator('.hd-pop-menu .hd-mi', {hasText: 'Tailwind'}).click();
    await page.waitForFunction(() => /Copied as Tailwind/.test((document.querySelector('.hd-toast') || {}).textContent || ''));
    eq((await page.evaluate(() => navigator.clipboard.readText())).trim(), '<div class="absolute left-[100px] top-[100px] w-[200px] h-[200px] bg-[#00FF00] outline outline-[4px] outline-black outline-offset-[-2px] rounded-full"></div>', 'Copy as code → Tailwind');

    /* ---- SVG: what Hoola writes comes back as the same layers ---- */
    step('SVG: what Hoola writes comes back as the same layers');
    const rt = await page.evaluate(async () => {
      const S = HD.store, H = HD.handoff, pg = HD.sel.page, sol = (c, o) => ({type: 'solid', color: c, opacity: o === undefined ? 1 : o, visible: true}), o = {};
      S.tx('seed', () => {
        o.post = S.create('FRAME', pg, {name: 'Round trip', x: 0, y: 2000, w: 800, h: 600, fills: [sol('#FFF4E0')]});
        S.create('RECT', o.post, {name: 'Blue', x: 40, y: 50, w: 200, h: 120, fills: [sol('#0000FF')], strokes: [sol('#111111')], strokeWeight: 4});
        S.create('RECT', o.post, {name: 'Round', x: 300, y: 50, w: 180, h: 100, radius: 20, fills: [sol('#22AA66', 0.5)]});
        S.create('ELLIPSE', o.post, {name: 'Dot', x: 520, y: 40, w: 160, h: 120, fills: [{type: 'linear', stops: [{pos: 0, color: '#FFFF00', opacity: 1}, {pos: 1, color: '#FF00FF', opacity: 1}], from: [0, 0.5], to: [1, 0.5], opacity: 1, visible: true}]});
        S.create('RECT', o.post, {name: 'Turned', x: 80, y: 260, w: 200, h: 80, rot: 30, fills: [sol('#AA2200')], strokes: [sol('#000000')], strokeWeight: 2, strokeAlign: 'inside'});
        S.create('LINE', o.post, {name: 'Rule', x: 350, y: 300, w: 240, rot: 20, strokes: [sol('#333333')], strokeWeight: 3});
        S.create('VECTOR', o.post, {name: 'Tri', x: 600, y: 250, w: 120, h: 100, path: 'M0 100L60 0L120 100Z', fills: [sol('#008888')]});
        S.create('TEXT', o.post, {name: 'Label', x: 60, y: 450, chars: 'Hello\nWorld', fontSize: 32, fontWeight: 700, fills: [sol('#222222')]});
        const g = S.create('GROUP', o.post, {name: 'Pair'});
        S.create('RECT', g, {name: 'G1', x: 400, y: 420, w: 60, h: 60, fills: [sol('#FF8800')]});
        S.create('ELLIPSE', g, {name: 'G2', x: 480, y: 430, w: 80, h: 40, fills: [sol('#8800FF')]});
      });
      await new Promise(r => setTimeout(r, 200));
      const r = await H.renderOne(o.post, {fmt: 'svg', scale: 1}), count0 = S.count();
      const got = await H.importSvg(r.text, {x: 2400, y: 2300});
      const dump = id => { const out = []; const go = (nid, d) => { const n = S.get(nid), b = S.worldBounds(nid); out.push([d, n.type, Math.round(b.x * 10) / 10, Math.round(b.y * 10) / 10, Math.round(b.w * 10) / 10, Math.round(b.h * 10) / 10, Math.round((n.rot || 0) * 10) / 10, (n.fills || []).length, (n.strokes || []).length, n.strokeAlign || '', n.radius || 0, n.chars || '']); for (const k of S.children(nid)) go(k, d + 1); }; go(id, 0); return out; };
      const a = dump(o.post), b = dump(got.id), made = S.count() - count0, undoable = S.canUndo();
      const same = await (async () => { const A = HD.render.toCanvas(o.post, 1, {bounds: 'box'}), B = HD.render.toCanvas(got.id, 1, {bounds: 'box'}), da = A.getContext('2d').getImageData(0, 0, 800, 600).data, db = B.getContext('2d').getImageData(0, 0, 800, 600).data; let sum = 0, bad = 0; for (let i = 0; i < da.length; i += 4) { const d = (Math.abs(da[i] - db[i]) + Math.abs(da[i + 1] - db[i + 1]) + Math.abs(da[i + 2] - db[i + 2])) / 3; sum += d; if (d > 40) bad++; } return [sum / (da.length / 4), bad]; })();
      S.undo(); const afterUndo = S.has(got.id), countBack = S.count() === count0; S.redo();
      return {a, b, made, nodes: got.nodes, undoable, afterUndo, countBack, same, sel: HD.sel.ids.slice(), head: r.text.slice(0, 60)};
    });
    ok(/^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg"/.test(rt.head), 'the SVG export is an SVG');
    eq(rt.b.length, rt.a.length, 'the same number of layers comes back: ' + rt.b.length); eq(rt.made, rt.nodes, 'and the import says how many it made');
    rt.a.forEach((row, i) => { const back = rt.b[i]; eq([back[0], back[1]], [row[0], row[1]], 'layer ' + i + ' has the same kind and depth (' + row[1] + ')');
      near(back[2] - 2000, row[2], 0.15, 'x of ' + row[1] + ' ' + i); near(back[3], row[3], 0.15, 'y of ' + row[1] + ' ' + i); near(back[4], row[4], 0.15, 'width of ' + row[1] + ' ' + i); near(back[5], row[5], 0.15, 'height of ' + row[1] + ' ' + i);
      near(back[6], row[6], 0.11, 'rotation'); eq(back.slice(7, 9), row.slice(7, 9), 'fills and strokes of ' + row[1] + ' ' + i); if (row[1] !== 'LINE' && row[8]) eq(back[9] || 'center', row[9] || 'center', 'stroke side'); eq(back[10], row[10], 'corner radius'); eq(back[11], row[11], 'text'); });
    ok(rt.same[0] < 1.5 && rt.same[1] < 800 * 600 * 0.004, 'and they look the same (mean ' + rt.same[0].toFixed(2) + ', ' + rt.same[1] + ' pixels off)');
    ok(rt.undoable && rt.afterUndo === false && rt.countBack, 'the whole import is ONE undo step');

    /* ---- a hostile SVG: nothing runs, nothing is fetched ---- */
    step('a hostile SVG: nothing runs, nothing is fetched');
    const before = requests.length;
    const hs = await page.evaluate(async (svg) => { const got = await HD.handoff.importSvg(svg, {x: -2000, y: 300}); const S = HD.store, list = []; S.walk(got.id, (id, n) => { list.push([n.type, n.name, n.fills ? n.fills.map(f => f.type + (f.color || '')).join() : '', n.chars || '']); return true; }); await new Promise(r => setTimeout(r, 700));
      return {list, left: got.left, pwned: window.__pwned === undefined ? null : window.__pwned, live: document.querySelectorAll('script[src*="evil"], foreignObject, iframe, img[src*="evil"]').length}; }, HOSTILE_SVG);
    eq(hs.pwned, null, 'no script, onload, onclick or javascript: link ran'); eq(hs.live, 0, 'nothing of the SVG was put into the page');
    eq(requests.slice(before).filter(u => !u.startsWith(origin)), [], 'no address outside the app was asked for'); eq(requests.slice(before).filter(u => /evil|invalid/.test(u)), [], 'no evil address at all');
    eq(hs.list, [['FRAME', 'SVG', '', ''], ['RECT', 'ok', 'solid#000000', ''], ['ELLIPSE', 'Ellipse', '', ''], ['TEXT', 'hi', 'solid#000000', 'hi']], 'the harmless shapes came in (a fill that points outside is no fill; the text keeps no outside entity)');
    ok(hs.left.unsafe >= 5 && hs.left.outside === 4, 'and it says what was left out: ' + JSON.stringify(hs.left)); ok(/were left out/.test(await toastOf(page)), 'in words too');
    const junk = await page.evaluate(async () => { const n0 = HD.store.count(), out = []; for (const t of ['not an svg at all', '<svg xmlns="http://www.w3.org/2000/svg"><rect', '<html><body>x</body></html>', '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>']) out.push(await HD.handoff.importSvg(t, {x: 0, y: 0})); return [out, HD.store.count() === n0]; });
    eq(junk, [[null, null, null, null], true], 'a broken or empty SVG adds nothing');
    /* the cap, in a file of its own (20,000 layers are not dragged through the rest of the walk) */
    const f2 = await (await page.request.post(origin + '/api/design/files', {headers: {Authorization: 'Bearer fixture-only'}, data: {name: 'Big SVG'}})).json();
    const big = await newPage(); await big.goto(base + '#/f/' + f2.id); await mounted(big);
    const cap = await big.evaluate(async () => { let s = '<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="2000">'; for (let i = 0; i < 20600; i++) s += '<rect x="' + (i % 200) * 10 + '" y="' + Math.floor(i / 200) * 10 + '" width="8" height="8"/>'; const t0 = performance.now(), got = await HD.handoff.importSvg(s + '</svg>', {x: 9000, y: 9000}); return [got.nodes, got.capped, Math.round(performance.now() - t0), HD.store.count(), HD.store.canUndo()]; });
    ok(cap[0] === 20000 && cap[1] === true && cap[3] === 20002, 'a huge SVG stops at 20,000 layers and says so: ' + cap); ok(/only the first 20,000/.test(await toastOf(big)), 'the cap is said in words');
    await big.waitForFunction(() => HD.store.pendingCount() === 0, null, {timeout: 60000}); eq(Object.keys(mock.files.get(f2.id).doc.nodes).length, 20002, 'and the server took them all');
    report.cap_ms = cap[2]; await big.close();

    /* ---- a real-world style SVG: the numbers, and the browser's own picture of it ---- */
    step("a real-world style SVG: the numbers, and the browser's own p");
    const cx = await page.evaluate(async (svg) => {
      const H = HD.handoff, S = HD.store, got = await H.importSvg(svg, {x: 320, y: -2000}, {name: 'shop'});
      const rows = []; const go = (id, d) => { const n = S.get(id), b = S.worldBounds(id); rows.push({d, t: n.type, name: n.name, x: +b.x.toFixed(2), y: +(b.y + 2240).toFixed(2), w: +b.w.toFixed(2), h: +b.h.toFixed(2), rot: n.rot || 0, sw: n.strokeWeight, fill: n.fills && n.fills[0] ? (n.fills[0].color || n.fills[0].type) : '', fo: n.fills && n.fills[0] ? n.fills[0].opacity : null, op: n.opacity, r: n.radius, dash: n.dash, cap: n.strokeCap, runs: n.runs, chars: n.chars, clip: n.clip, from: n.fills && n.fills[0] && n.fills[0].from, to: n.fills && n.fills[0] && n.fills[0].to, stops: n.fills && n.fills[0] && n.fills[0].stops, fw: n.fontWeight, fs: n.fontSize}); for (const k of S.children(id)) go(k, d + 1); }; go(got.id, 0);
      await HD.render.ready(got.id, 4000);
      const cv = HD.render.toCanvas(got.id, 1, {bounds: 'box', bg: '#FFFFFF'}), im = new Image();
      await new Promise((res, rej) => { im.onload = res; im.onerror = () => rej(new Error('the browser could not draw the SVG')); im.src = URL.createObjectURL(new Blob([svg], {type: 'image/svg+xml'})); });
      const ref = document.createElement('canvas'); ref.width = cv.width; ref.height = cv.height; const rc = ref.getContext('2d'); rc.fillStyle = '#fff'; rc.fillRect(0, 0, ref.width, ref.height); rc.drawImage(im, 0, 0, ref.width, ref.height);
      const diff = (A, B) => { const a = A.getContext('2d').getImageData(0, 0, A.width, A.height).data, b = B.getContext('2d').getImageData(0, 0, A.width, A.height).data; let sum = 0, bad = 0; for (let i = 0; i < a.length; i += 4) { const d = (Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2])) / 3; sum += d; if (d > 40) bad++; } return [sum / (a.length / 4), bad]; };
      const good = diff(cv, ref);
      /* the check must be able to fail: nudge one layer and the pictures differ */
      const leaf = rows.find(r => r.name === 'leaf'); let moved = null; S.walk(got.id, (id, n) => { if (n.name === 'leaf') moved = id; return true; });
      S.tx('nudge', () => S.set(moved, {x: S.get(moved).x + 30})); const broken = diff(HD.render.toCanvas(got.id, 1, {bounds: 'box', bg: '#FFFFFF'}), ref); S.undo(); void leaf;
      return {rows, size: [cv.width, cv.height], good, broken, nodes: got.nodes, left: got.left, sel: HD.sel.ids[0] === got.id, centre: (() => { const b = S.worldBounds(got.id); return [b.x + b.w / 2, b.y + b.h / 2]; })()};
    }, COMPLEX_SVG);
    const R0 = name => cx.rows.find(r => r.name === name), byT = (t, i) => cx.rows.filter(r => r.t === t)[i];
    eq(cx.size, [640, 480], 'the frame takes the size of the SVG (width / height, not the viewBox)'); eq(cx.centre, [320, -2000], 'centred where it was dropped'); ok(cx.sel, 'and selected');
    eq([cx.rows[0].t, cx.rows[0].name, cx.rows[0].clip], ['FRAME', 'shop', true], 'one frame holds it'); eq(Object.values(cx.left).reduce((a, b) => a + b, 0), 0, 'nothing of it was left out');
    const sky = cx.rows[0]; eq([sky.t, sky.x, sky.y, sky.w, sky.h, sky.fill], ['FRAME', 0, 0, 640, 480, 'linear'], 'the background rectangle is the fill of the frame: viewBox 320 x 240 in 640 x 480 = scale 2');
    eq([sky.from, sky.to], [[0, 0], [0, 1]], 'a userSpaceOnUse gradient in the terms of its box'); eq(sky.stops, [{pos: 0, color: '#DDEEFF', opacity: 1}, {pos: 1, color: '#88AAEE', opacity: 0.8}], 'stops from style attributes, with their opacity');
    const cards = R0('cards'); eq([cards.t, cards.x, cards.y, cards.w, cards.h, cards.r, cards.sw, cards.fill, cards.clip], ['FRAME', 40, 40, 240, 160, 20, 4, '#FFFFFF', true], 'a group that starts with its background rectangle becomes a frame (class .card: fill, stroke 2 x 2, rx 10 x 2)');
    const acc = cx.rows.find(r => r.t === 'RECT' && r.fill === 'linear' && r.d === 3); eq([acc.x, acc.y, acc.w, acc.h, acc.fo], [60, 60, 120, 40, 0.5], 'translate(20 20) translate(10 10) scale(2), .accent.soft: gradient at half opacity');
    eq([acc.from, acc.to, acc.stops.map(s => s.color)], [[0, 0], [1, 0], ['#FF8A00', '#E52E71']], 'an objectBoundingBox gradient, rgb() stop');
    const glow = cx.rows.find(r => r.t === 'ELLIPSE' && r.fill === 'radial'); eq([glow.x, glow.y, glow.w, glow.h, glow.from, glow.to, glow.stops.map(s => s.color)], [188, 88, 64, 64, [0.5, 0.5], [1, 0.5], ['#FFFFFF', '#000080']], 'circle r 8 under scale 4, radial gradient, named colours');
    const leaf = R0('leaf'); eq([leaf.t, leaf.rot, leaf.fill], ['RECT', 30, '#2E9E5B'], 'a rotated rectangle stays a rectangle (#leaf rule)'); near(leaf.x, 58.64, 0.02, 'leaf box x'); near(leaf.y, 121.57, 0.02, 'leaf box y'); near(leaf.w, 81.28, 0.02, 'leaf box w'); near(leaf.h, 60.78, 0.02, 'leaf box h');
    const egg = cx.rows.find(r => r.t === 'ELLIPSE' && r.rot === -15); eq([egg.sw, egg.fill], [6, 'linear'], 'rotate(-15 80 170): an ellipse with a turn; stroke 3 x 2'); near(egg.x + egg.w / 2, 160, 0.02, 'its centre x'); near(egg.y + egg.h / 2, 340, 0.02, 'its centre y');
    eq([egg.from, egg.to], [[1, 0], [1, 1]], 'href + gradientTransform rotate(90 .5 .5): the borrowed gradient now runs top to bottom');
    const tri = byT('VECTOR', 0); eq([tri.x, tri.y, tri.w, tri.h, tri.fill, tri.op, tri.sw], [280, 240, 120, 120, '#FFD700', 0.8, 8], 'a polygon is a path; opacity on the layer');
    const skew = byT('VECTOR', 1); eq([skew.fill, skew.y, skew.h], ['#7744CC', 260, 100], 'a skewed path is baked into a path'); near(skew.x, 363.48, 0.05, 'skewX(-12): left edge'); near(skew.w, 157.46, 0.05, 'skewX(-12): width');
    const line = byT('LINE', 0); eq([line.sw, line.dash, line.cap], [8, [12, 6], 'round'], 'a line: stroke, dashes and caps from a class, scaled'); near(line.rot, 2.05, 0.01, 'its angle'); near(line.x, 40, 0.05, 'line x'); near(line.w, 560, 0.05, 'line w');
    const pips = cx.rows.filter(r => r.name === 'pip'); eq(pips.map(p => [p.t, p.x, p.y, p.w, p.h]), [['GROUP', 488, 386, 24, 36], ['GROUP', 542, 374, 36, 54]], '<use> of a group from <defs>, once moved and once scaled 1.5');
    const badge = R0('badge'), tile = cx.rows[cx.rows.indexOf(badge) + 1]; eq([badge.t, badge.x, badge.y, badge.w, badge.h], ['GROUP', 300, 40, 80, 80], '<use> of a <symbol> with a viewBox'); eq([tile.fill, tile.r], ['#1466B8', 16], 'hsl() colour, rx 4 under scale 4');
    const clipF = R0('Clip'), clipKid = cx.rows[cx.rows.indexOf(clipF) + 1]; eq([clipF.t, clipF.x, clipF.y, clipF.w, clipF.h, clipF.clip], ['FRAME', 400, 40, 200, 140, true], 'a rectangular clipPath is a clipping frame'); eq([clipKid.t, clipKid.x, clipKid.y, clipKid.w], ['ELLIPSE', 400, 10, 200], 'with the circle inside, cut by it');
    const txt = byT('TEXT', 0); eq([txt.chars, txt.fill, txt.fw, txt.fs, txt.runs], ['Shop open', '#112233', 700, 24, [{s: 5, e: 9, fills: [{type: 'solid', color: '#CC0000', opacity: 1, visible: true}]}]], 'text with a coloured tspan = one text layer with a style run'); near(txt.x + txt.w / 2, 320, 0.6, 'text-anchor middle: centred on x 160 x 2');
    ok(!cx.rows.some(r => r.fill === '#FF0000'), 'display:none is not imported');
    ok(cx.good[0] < 1.5 && cx.good[1] < 640 * 480 * 0.004, 'pixel by pixel it matches the browser’s own drawing of the SVG: mean ' + cx.good[0].toFixed(2) + ', ' + cx.good[1] + ' pixels off');
    ok(cx.broken[1] > 400, 'and the comparison can fail: one nudged layer gives ' + cx.broken[1] + ' pixels off');
    report.svg = {layers: cx.nodes, mean_diff: +cx.good[0].toFixed(3), pixels_off: cx.good[1]};
    await page.evaluate(() => HD.render.zoomToFit(HD.sel.ids)); await page.waitForTimeout(350); await shot(page, 'svg-import');

    /* ---- pictures: the picker (Ctrl+Shift+K), a drop, a paste ---- */
    step('pictures: the picker (Ctrl+Shift+K), a drop, a paste');
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hd-pics-'));
    fs.writeFileSync(path.join(dir, 'red card.png'), pngBytes(300, 200, [200, 30, 30])); fs.writeFileSync(path.join(dir, 'blue.png'), pngBytes(120, 120, [30, 30, 200]));
    fs.writeFileSync(path.join(dir, 'very wide.png'), pngBytes(5000, 100, [30, 160, 60])); fs.writeFileSync(path.join(dir, 'fake.png'), '<html>not a picture</html>');
    await page.evaluate(() => { HD.sel.clear(); HD.render.setView({x: 700, y: 400, zoom: 0.1}); }); await page.waitForTimeout(100);
    const nBefore = await page.evaluate(() => HD.store.count()), postsBefore = mock.log.rest.filter(r => /POST .*\/assets$/.test(r)).length;
    await page.locator('canvas.hd-canvas').focus();
    let [fc] = await Promise.all([page.waitForEvent('filechooser'), page.keyboard.press('Control+Shift+K')]);
    await fc.setFiles(['red card.png', 'blue.png', 'very wide.png', 'fake.png'].map(f => path.join(dir, f)));
    await page.waitForFunction(() => HD.sel.ids.length === 3, null, {timeout: 20000});
    const pics = await page.evaluate(() => HD.sel.ids.map(id => { const n = HD.store.get(id); return [n.type, n.name, n.w, n.h, n.fills[0].type, n.fills[0].mode, /^[0-9a-f]{64}$/.test(n.fills[0].hash), n.x, n.y + n.h / 2]; }));
    eq(pics.map(p => p.slice(0, 7)), [['RECT', 'red card', 300, 200, 'image', 'fill', true], ['RECT', 'blue', 120, 120, 'image', 'fill', true], ['RECT', 'very wide', 4096, 82, 'image', 'fill', true]], 'pictures land at their own size as image fills; one over 4096 px is made smaller');
    eq([pics[1][7] - pics[0][7], pics[2][7] - pics[1][7]], [324, 144], 'in one tidy row, 24 apart'); ok(Math.abs(pics[0][8] - pics[1][8]) <= 1 && Math.abs(pics[1][8] - pics[2][8]) <= 1, 'on one centre line');
    eq(mock.log.rest.filter(r => /POST .*\/assets$/.test(r)).length - postsBefore, 3, 'each was uploaded as an asset of the file'); ok(/Not placed: fake\.png/.test(await toastOf(page)), 'a file that is not a picture is refused by its content, with its name');
    eq(await page.evaluate(n => { HD.store.undo(); const gone = HD.store.count() === n; HD.store.redo(); return [gone, HD.store.count() === n + 3]; }, nBefore), [true, true], 'three pictures are ONE undo step');
    /* drop an SVG file on the canvas: real layers, centred on the pointer */
    await page.evaluate(() => { HD.sel.clear(); HD.render.setView({x: 3000, y: 3000, zoom: 1}); }); await page.waitForTimeout(100);
    const cbox = await page.locator('canvas.hd-canvas').boundingBox();
    const dt = await page.evaluateHandle(() => { const d = new DataTransfer(); d.items.add(new File(['<svg xmlns="http://www.w3.org/2000/svg" width="60" height="40"><rect width="60" height="40" fill="teal"/><circle cx="30" cy="20" r="10" fill="#fff"/></svg>'], 'logo mark.svg', {type: 'image/svg+xml'})); return d; });
    await page.dispatchEvent('canvas.hd-canvas', 'dragover', {dataTransfer: dt, clientX: cbox.x + 300, clientY: cbox.y + 400}); await page.dispatchEvent('canvas.hd-canvas', 'drop', {dataTransfer: dt, clientX: cbox.x + 300, clientY: cbox.y + 400});
    await page.waitForFunction(() => HD.sel.ids.length === 1 && HD.store.get(HD.sel.ids[0]).name === 'logo mark', null, {timeout: 10000});
    const dropped = await page.evaluate(() => { const id = HD.sel.ids[0], n = HD.store.get(id), b = HD.store.worldBounds(id), c = HD.render.worldToScreen(b.x + b.w / 2, b.y + b.h / 2); return [n.type, n.w, n.h, HD.store.children(id).map(k => HD.store.get(k).type), HD.store.prop(id, 'fills').length ? HD.store.prop(id, 'fills')[0].color : '', Math.round(c[0]), Math.round(c[1])]; });
    eq(dropped, ['FRAME', 60, 40, ['ELLIPSE'], '#008080', 300, 400], 'a dropped SVG file: a frame with real shapes, centred under the pointer (not a flat picture)');
    /* paste SVG text (the editor's paste reaches the import through the hook), then a picture file */
    await page.evaluate(() => { HD.sel.clear(); HD.render.setView({x: 6000, y: 6000, zoom: 1}); HD.tools.canvas.focus(); const d = new DataTransfer(); d.setData('text/plain', '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 2l3 7h7l-6 4 2 8-6-5-6 5 2-8-6-4h7z" fill="#F5A623"/></svg>'); HD.tools.canvas.dispatchEvent(new ClipboardEvent('paste', {clipboardData: d, bubbles: true, cancelable: true})); });
    await page.waitForFunction(() => HD.sel.ids.length === 1 && HD.store.get(HD.sel.ids[0]).type === 'FRAME' && HD.store.get(HD.sel.ids[0]).w === 24, null, {timeout: 10000});
    eq(await page.evaluate(() => { const id = HD.sel.ids[0]; return HD.store.children(id).map(k => [HD.store.get(k).type, HD.store.get(k).w, HD.store.get(k).h, HD.store.get(k).fills[0].color]); }), [['VECTOR', 20, 19, '#F5A623']], 'pasted SVG text is a vector layer');
    await page.evaluate(async (b64) => { HD.sel.clear(); HD.render.setView({x: 9000, y: 9000, zoom: 1}); const bin = atob(b64), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); const d = new DataTransfer(); d.items.add(new File([u], 'from clipboard.png', {type: 'image/png'})); HD.tools.canvas.focus(); HD.tools.canvas.dispatchEvent(new ClipboardEvent('paste', {clipboardData: d, bubbles: true, cancelable: true})); }, pngBytes(64, 48, [10, 200, 200]).toString('base64'));
    await page.waitForFunction(() => HD.sel.ids.length === 1 && HD.store.get(HD.sel.ids[0]).name === 'from clipboard', null, {timeout: 10000});
    eq(await page.evaluate(() => { const n = HD.store.get(HD.sel.ids[0]); return [n.type, n.w, n.h, n.fills[0].type, HD.store.children(HD.sel.page).includes(HD.sel.ids[0])]; }), ['RECT', 64, 48, 'image', true], 'a pasted picture: a rectangle of its own size with the picture as its fill');
    /* a picture inside an SVG (data: address) is uploaded and becomes an image fill */
    const emb = await page.evaluate(async (b64) => { const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><image href="data:image/png;base64,' + b64 + '" x="10" y="20" width="64" height="48"/><image href="data:text/html;base64,PGI+eDwvYj4=" width="10" height="10"/></svg>'; const got = await HD.handoff.importSvg(svg, {x: 12000, y: 12000}); const k = HD.store.children(got.id).map(id => HD.store.get(id)); return [k.length, k[0].type, k[0].x, k[0].y, k[0].w, k[0].h, k[0].fills[0].type, /^[0-9a-f]{64}$/.test(k[0].fills[0].hash), got.left.outside]; }, pngBytes(64, 48, [200, 200, 10]).toString('base64'));
    eq(emb, [1, 'RECT', 10, 20, 64, 48, 'image', true, 1], 'an embedded PNG becomes an asset; a data: address that is not a picture is left out');

    /* ---- Inspect: the values, the colours, the code ---- */
    step('Inspect: the values, the colours, the code');
    const card = await page.evaluate(async () => {
      const S = HD.store, pg = HD.sel.page, sol = (c, o) => ({type: 'solid', color: c, opacity: o === undefined ? 1 : o, visible: true}), o = {};
      S.tx('card', () => {
        o.board = S.create('FRAME', pg, {name: 'Board', x: 0, y: -4000, w: 480, h: 360, fills: [sol('#F2F2F7')]});
        o.card = S.create('FRAME', o.board, {name: 'Card', x: 40, y: 30, w: 300, h: 100, fills: [sol('#FFFFFF')], radius: [20, 4, 20, 4], strokes: [sol('#3355AA')], strokeWeight: 4, strokeAlign: 'inside',
          effects: [{type: 'drop', x: 0, y: 6, blur: 16, spread: 2, color: '#000000', opacity: 0.3, visible: true}], layout: {mode: 'h', gap: 10, pad: [12, 16, 12, 16], alignMain: 'start', alignCross: 'center', wrap: false}});
        o.chip = S.create('RECT', o.card, {name: 'Chip', w: 60, h: 40, radius: 8, fills: [{type: 'linear', stops: [{pos: 0, color: '#FF8A00', opacity: 1}, {pos: 1, color: '#E52E71', opacity: 1}], from: [0.1, 0.2], to: [0.9, 0.8], opacity: 1, visible: true}]});
        o.grow = S.create('RECT', o.card, {name: 'Grow', w: 20, h: 30, sizeH: 'fill', fills: [sol('#22AA66')]});
        o.dot = S.create('ELLIPSE', o.card, {name: 'Dot', w: 36, h: 36, fills: [{type: 'radial', stops: [{pos: 0, color: '#FFFFFF', opacity: 1}, {pos: 1, color: '#0000AA', opacity: 1}], from: [0.5, 0.5], to: [1, 0.5], opacity: 1, visible: true}], strokes: [sol('#000000')], strokeWeight: 2, strokeAlign: 'outside'});
        o.abs = S.create('RECT', o.board, {name: 'Turned', x: 60, y: 200, w: 140, h: 70, rot: 20, opacity: 0.8, fills: [sol('#AA2244'), sol('#0000FF', 0.3)], strokes: [sol('#111111')], strokeWeight: 6, strokeAlign: 'center', radius: 10});
        o.box = S.create('FRAME', o.board, {name: 'Box', x: 260, y: 180, w: 180, h: 140, fills: [sol('#FFFFFF')], strokes: [sol('#FF0000')], strokeWeight: 5, strokeAlign: 'inside'});
        o.in1 = S.create('RECT', o.box, {name: 'In', x: 20, y: 30, w: 80, h: 50, fills: [{type: 'angular', stops: [{pos: 0, color: '#FF0000', opacity: 1}, {pos: 0.5, color: '#00FF00', opacity: 1}, {pos: 1, color: '#0000FF', opacity: 1}], from: [0.5, 0.5], to: [1, 0.5], opacity: 1, visible: true}]});
        o.peek = S.create('ELLIPSE', o.box, {name: 'Peek', x: 130, y: 90, w: 80, h: 80, fills: [sol('#FFAA00')]});
        o.title = S.create('TEXT', o.board, {name: 'Title', x: 40, y: 150, chars: 'It\'s $5\nonly', font: 'Inter', fontSize: 18, fontWeight: 600, lineHeight: 24, letterSpacing: 0.5, align: 'center', textCase: 'upper', fills: [sol('#1A1A1F', 0.5)]});
      });
      await new Promise(r => setTimeout(r, 300));
      const H = HD.handoff, tree = id => ({css: H.code.cssPairs(id), kids: S.get(id).type === 'TEXT' ? [] : S.children(id).map(tree)});
      S.tx('hide', () => S.set(o.title, {visible: false}));                      /* text is compared by its code, not by pixels (the test has no web font) */
      const r = await H.renderOne(o.board, {fmt: 'png', scale: 1}), buf = new Uint8Array(await r.blob.arrayBuffer()); let s = ''; for (const c of buf) s += String.fromCharCode(c);
      const out = {ids: o, tree: tree(o.board), png: btoa(s), grown: S.get(o.grow).w, css: {}, tw: {}}; S.undo();
      for (const k of ['card', 'chip', 'grow', 'dot', 'abs', 'box', 'in1', 'title']) { out.css[k] = H.code.css(o[k]); out.tw[k] = H.code.tailwindClasses(o[k]).join(' '); }
      out.flutter = H.code.flutter(o.card); out.flutterText = H.code.flutter(o.title); out.twHtml = H.code.tailwind(o.card);
      HD.sel.set([o.card]); HD.render.zoomToFit([o.board]);
      return out;
    });
    eq(card.grown, 152, 'the layout made the "fill" child 152 wide (300 - 2 x 16 - 60 - 36 - 2 x 10)');
    eq(card.css.card, ['/* Card */', 'position: absolute;', 'left: 40px;', 'top: 30px;', 'width: 300px;', 'height: 100px;', 'display: flex;', 'flex-direction: row;', 'align-items: center;', 'gap: 10px;', 'padding: 8px 12px;', 'box-sizing: border-box;', 'background: #FFFFFF;',
      'border: 4px solid #3355AA;', 'border-radius: 20px 4px;', 'box-shadow: 0 6px 16px 2px rgba(0, 0, 0, 0.3);', 'overflow: hidden;'].join('\n'), 'CSS of an auto layout card (the padding is counted from inside its 4px border)');
    eq(card.css.chip, '/* Chip */\nwidth: 60px;\nheight: 40px;\nbackground: linear-gradient(116.57deg, #FF8A00 12.5%, #E52E71 87.5%);\nborder-radius: 8px;', 'a gradient: the angle and the stop places CSS needs for the same picture');
    eq(card.css.grow, '/* Grow */\nflex: 1 1 0;\nheight: 30px;\nbackground: #22AA66;', 'a child that fills the row');
    eq(card.css.dot, '/* Dot */\nwidth: 36px;\nheight: 36px;\nbackground: radial-gradient(circle 18px at 50% 50%, #FFFFFF 0%, #0000AA 100%);\noutline: 2px solid #000000;\nborder-radius: 50%;', 'an ellipse with an outside stroke');
    eq(card.css.abs, '/* Turned */\nposition: absolute;\nleft: 60px;\ntop: 200px;\nwidth: 140px;\nheight: 70px;\nbackground: linear-gradient(rgba(0, 0, 255, 0.3), rgba(0, 0, 255, 0.3)), #AA2244;\noutline: 6px solid #111111;\noutline-offset: -3px;\nborder-radius: 10px;\nopacity: 0.8;\ntransform: rotate(20deg);', 'two fills, a centre stroke, opacity, rotation');
    eq(card.css.in1, '/* In */\nposition: absolute;\nleft: 15px;\ntop: 25px;\nwidth: 80px;\nheight: 50px;\nbackground: conic-gradient(from 90deg at 50% 50%, #FF0000 0deg, #00FF00 180deg, #0000FF 360deg);', 'a child of a frame with a 5px inside border: placed from inside that border');
    eq(card.css.title, '/* Title */\nposition: absolute;\nleft: 40px;\ntop: 150px;\ncolor: rgba(26, 26, 31, 0.5);\nfont-family: "Inter", sans-serif;\nfont-size: 18px;\nfont-weight: 600;\nline-height: 24px;\nletter-spacing: 0.5px;\ntext-align: center;\ntext-transform: uppercase;\nwhite-space: pre;', 'typography');
    eq(card.tw.card, 'absolute left-10 top-[30px] w-[300px] h-[100px] flex items-center gap-2.5 px-3 py-2 bg-white border-4 border-[#3355AA] rounded-tl-[20px] rounded-tr-[4px] rounded-br-[20px] rounded-bl-[4px] shadow-[0_6px_16px_2px_rgba(0,0,0,0.3)] overflow-hidden', 'Tailwind: scale steps where they are exact, arbitrary values elsewhere');
    eq(card.tw.chip, 'w-[60px] h-10 bg-[linear-gradient(116.57deg,#FF8A00_12.5%,#E52E71_87.5%)] rounded-lg'); eq(card.tw.grow, 'flex-1 h-[30px] bg-[#22AA66]');
    eq(card.tw.title, 'absolute left-10 top-[150px] text-[rgba(26,26,31,0.5)] font-[\'Inter\'] text-[18px] font-semibold leading-[24px] tracking-[0.5px] text-center uppercase whitespace-pre');
    eq(card.twHtml.split('\n').filter(Boolean).length, 5, 'Tailwind markup: the card and its three children'); ok(/^<div class="absolute left-10[^"]*">\n  <div class="w-\[60px\]/.test(card.twHtml), 'nested');
    eq(card.flutter, ['Container(', '  width: 300,', '  height: 100,', '  padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),', '  clipBehavior: Clip.antiAlias,', '  decoration: BoxDecoration(', '    color: Color(0xFFFFFFFF),',
      '    border: Border.all(color: Color(0xFF3355AA), width: 4, strokeAlign: BorderSide.strokeAlignInside),', '    borderRadius: BorderRadius.only(topLeft: Radius.circular(20), topRight: Radius.circular(4), bottomRight: Radius.circular(20), bottomLeft: Radius.circular(4)),',
      '    boxShadow: [BoxShadow(color: Color(0x4D000000), offset: Offset(0, 6), blurRadius: 16, spreadRadius: 2)],', '  ),', '  child: Row(', '    children: [', '      Container(', '        width: 60,', '        height: 40,', '        decoration: BoxDecoration(',
      '          gradient: LinearGradient(begin: Alignment(-0.8, -0.6), end: Alignment(0.8, 0.6), colors: [Color(0xFFFF8A00), Color(0xFFE52E71)], stops: [0, 1]),', '          borderRadius: BorderRadius.circular(8),', '        ),', '      ),', '      SizedBox(width: 10),',
      '      Expanded(', '        child: Container(', '          height: 30,', '          decoration: BoxDecoration(', '            color: Color(0xFF22AA66),', '          ),', '        ),', '      ),', '      SizedBox(width: 10),', '      Container(', '        width: 36,', '        height: 36,',
      '        decoration: BoxDecoration(', '          gradient: RadialGradient(center: Alignment(0, 0), radius: 0.5, colors: [Color(0xFFFFFFFF), Color(0xFF0000AA)], stops: [0, 1]),', '          border: Border.all(color: Color(0xFF000000), width: 2, strokeAlign: BorderSide.strokeAlignOutside),', '          shape: BoxShape.circle,',
      '        ),', '      ),', '    ],', '  ),', ')', ''].join('\n'), 'Flutter: Container / BoxDecoration / Row with the gap as SizedBox and the filling child Expanded');
    eq(card.flutterText, ['Text(', '  \'IT\\\'S \\$5\\nONLY\',', '  textAlign: TextAlign.center,', '  style: TextStyle(', '    color: Color(0x801A1A1F),', '    fontFamily: \'Inter\',', '    fontSize: 18,', '    fontWeight: FontWeight.w600,', '    height: 1.333,', '    letterSpacing: 0.5,', '  ),', ')', ''].join('\n'), 'Flutter Text: the string is escaped, the case applied, line height as a factor');
    /* the CSS is put on real elements in a clean page and compared with the canvas, pixel by pixel */
    const dom = await browser.newPage({viewport: {width: 600, height: 500}});
    await dom.setContent('<!doctype html><html><body style="margin:0;background:#fff"><div id="root"></div></body></html>');
    await dom.evaluate(tree => { const mk = t => { const el = document.createElement('div'); for (const kv of t.css) el.style.setProperty(kv[0], kv[1]); for (const k of t.kids) el.appendChild(mk(k)); return el; }; const root = mk(tree); root.style.setProperty('top', '0'); document.getElementById('root').appendChild(root); }, card.tree);
    const domPng = await dom.screenshot({clip: {x: 0, y: 0, width: 480, height: 360}});
    const cssDiff = await dom.evaluate(async pair => { const load = async u => { const im = new Image(); await new Promise(r => { im.onload = r; im.src = u; }); const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const x = c.getContext('2d'); x.drawImage(im, 0, 0); return x.getImageData(0, 0, c.width, c.height); };
      const A = await load(pair[0]), B = await load(pair[1]); let sum = 0, bad = 0; for (let i = 0; i < A.data.length; i += 4) { const d = (Math.abs(A.data[i] - B.data[i]) + Math.abs(A.data[i + 1] - B.data[i + 1]) + Math.abs(A.data[i + 2] - B.data[i + 2])) / 3; sum += d; if (d > 48) bad++; } return [A.width, A.height, B.width, B.height, sum / (A.data.length / 4), bad]; },
      ['data:image/png;base64,' + card.png, 'data:image/png;base64,' + domPng.toString('base64')]);
    await dom.close();
    eq(cssDiff.slice(0, 4), [480, 360, 480, 360]); ok(cssDiff[4] < 1.2 && cssDiff[5] < 480 * 360 * 0.004, 'the CSS draws what the canvas draws: mean difference ' + cssDiff[4].toFixed(2) + ', ' + cssDiff[5] + ' pixels off');
    report.css = {mean_diff: +cssDiff[4].toFixed(3), pixels_off: cssDiff[5]};
    /* the tab itself */
    await page.locator('.hd-right .hd-tab', {hasText: 'Inspect'}).click(); await page.waitForSelector('.hdx-inspect .hdx-code');
    eq(await page.locator('.hdx-inspect .hd-selname').textContent(), 'Card'); eq((await page.locator('.hdx-code').textContent()), card.css.card, 'the Inspect tab shows the CSS of the selection');
    const kvs = await page.locator('.hdx-inspect .hdx-kv').evaluateAll(els => els.map(e => e.querySelector('.hdx-k').textContent + '=' + e.querySelector('.hdx-v').textContent));
    ok(['X=40', 'Y=30', 'W=300', 'H=100', 'Radius=20 4 20 4', 'Stroke=4 inside', 'Direction=Row', 'Gap=10', 'Padding=12 16', 'Top=30', 'Right=140', 'Bottom=230', 'Left=40'].every(k => kvs.includes(k)), 'size, place, auto layout and the space to the parent: ' + kvs.join(' '));
    eq(await page.locator('.hdx-color .hdx-cv').allTextContents(), ['#FFFFFF', '#3355AA', '#0000004D', '#FF8A00', '#E52E71', '#22AA66', '#0000AA', '#000000'], 'the colours of the card and what is in it, as HEX');
    await page.locator('.hdx-inspect .hd-segb', {hasText: 'RGB'}).click(); await page.waitForFunction(() => /^rgb/.test(document.querySelector('.hdx-color .hdx-cv').textContent));
    eq((await page.locator('.hdx-color .hdx-cv').allTextContents()).slice(0, 3), ['rgb(255, 255, 255)', 'rgb(51, 85, 170)', 'rgba(0, 0, 0, 0.3)']);
    await page.locator('.hdx-color').nth(1).click(); await page.waitForFunction(() => /Copied rgb\(51, 85, 170\)/.test(document.querySelector('.hd-toast').textContent)); eq(await page.evaluate(() => navigator.clipboard.readText()), 'rgb(51, 85, 170)', 'a click copies the colour');
    await page.locator('.hdx-inspect .hd-segb', {hasText: 'HSL'}).click(); await page.waitForFunction(() => /^hsl/.test(document.querySelector('.hdx-color .hdx-cv').textContent));
    eq((await page.locator('.hdx-color .hdx-cv').allTextContents()).slice(1, 3), ['hsl(223, 54%, 43%)', 'hsla(0, 0%, 0%, 0.3)']); eq(await page.evaluate(() => localStorage.getItem('hd.inspect.color')), 'hsl', 'the colour format is remembered');
    await page.locator('.hdx-inspect .hd-segb', {hasText: 'Flutter'}).click(); await page.waitForFunction(() => /^Container\(/.test(document.querySelector('.hdx-code').textContent)); eq(await page.locator('.hdx-code').textContent(), card.flutter.trim());
    await page.locator('.hdx-copy').click(); await page.waitForFunction(() => /Copied as Flutter/.test(document.querySelector('.hd-toast').textContent)); eq(await page.evaluate(() => navigator.clipboard.readText()), card.flutter, 'Copy takes the code');
    await page.locator('.hdx-inspect .hd-segb', {hasText: 'Tailwind'}).click(); await page.waitForFunction(() => /^<div class=/.test(document.querySelector('.hdx-code').textContent)); eq(await page.evaluate(() => localStorage.getItem('hd.inspect.code')), 'tailwind');
    await page.evaluate(id => { HD.store.tx('m', () => HD.store.set(id, {x: 44})); }, card.ids.card); await page.waitForFunction(() => /left-11/.test(document.querySelector('.hdx-code').textContent), null, {timeout: 4000}); report.checks++;     /* the tab follows an edit */
    await page.evaluate(() => HD.store.undo());
    await page.evaluate(() => HD.sel.set(['9:1'])); await page.waitForFunction(() => document.querySelectorAll('.hdx-asset').length === 1);
    eq(await page.locator('.hdx-asset .hdx-ameta').textContent(), 'PNG 1x, JPG 512w', 'Assets lists the layers that have export settings');
    [dl] = await Promise.all([page.waitForEvent('download'), page.locator('.hdx-asset .hd-ib').click()]); eq(dl.suggestedFilename(), 'Post 1080.zip', 'and exports them from there');
    await page.evaluate(id => HD.sel.set([id]), card.ids.card); await page.waitForTimeout(200);
    eq(await layout(page), [], 'layout with the Inspect tab, light'); await shot(page, 'inspect-light');

    /* ---- Save a copy as .hoola.json, import it into a new file ---- */
    step('Save a copy as .hoola.json, import it into a new file');
    await page.evaluate(() => HD.sel.clear());
    [dl] = await Promise.all([page.waitForEvent('download'), page.evaluate(() => { HD.ui.run('saveCopy'); })]);
    eq(dl.suggestedFilename(), 'Shop poster.hoola.json'); const copyPath = await save(dl, 'copy.hoola.json'), copy = JSON.parse(fs.readFileSync(copyPath, 'utf8'));
    const mine = await page.evaluate(() => ({n: HD.store.count(), tops: HD.store.children(HD.sel.page).map(k => { const n = HD.store.get(k), b = HD.store.worldBounds(k); return [n.type, n.name, b.x, b.y, b.w, b.h, HD.store.children(k).length].join('|'); }), hashes: (() => { const s = new Set(); HD.store.walk(HD.store.ROOT, (id, n) => { for (const f of (n.fills || [])) if (f.type === 'image') s.add(f.hash); return true; }); return Array.from(s).sort(); })()}));
    eq([copy.format, copy.version, copy.name, copy.node_count, Object.keys(copy.nodes).length], ['hoola-design', 1, 'Shop poster', mine.n, mine.n], 'the copy is the whole document as JSON');
    eq(Object.keys(copy.assets).sort(), mine.hashes, 'every picture is listed by its hash'); ok(mine.hashes.length >= 5 && Object.values(copy.assets).every(a => a && a.type === 'image/png' && a.data.length > 20), 'and is inside the file too');
    const filesBefore = mock.files.size;
    [fc] = await Promise.all([page.waitForEvent('filechooser'), page.evaluate(() => { HD.ui.run('importCopy'); })]); await fc.setFiles(copyPath);
    await page.waitForFunction(() => HD.app.file && HD.app.file.id !== 'f1' && HD.ui.mounted && HD.net.status === 'live', null, {timeout: 30000}); await page.waitForTimeout(500);
    const back = await page.evaluate(() => ({id: HD.app.file.id, name: HD.app.file.name, n: HD.store.count(), pages: HD.store.pages().length, tops: HD.store.children(HD.sel.page).map(k => { const n = HD.store.get(k), b = HD.store.worldBounds(k); return [n.type, n.name, b.x, b.y, b.w, b.h, HD.store.children(k).length].join('|'); }), sync: HD.store.syncCheck ? HD.store.syncCheck() : true}));
    eq(mock.files.size, filesBefore + 1, 'the import made ONE new file'); eq([back.name, back.n, back.pages], ['Shop poster', mine.n, 1], 'with the same name, every layer and no extra page'); eq(back.tops, mine.tops, 'the same layers in the same places');
    const srv = mock.files.get(back.id).doc.nodes, oldIds = new Set(Object.keys(copy.nodes).filter(k => k !== '0:0' && k !== '0:1'));
    eq(Object.keys(srv).length, mine.n, 'the server has them all'); eq(Object.keys(srv).filter(k => oldIds.has(k) && /^9:/.test(k)).length, 0, 'under fresh ids'); ok(Object.values(srv).every(n => !n.parent || srv[n.parent]), 'every layer has its parent');
    report.copy = {layers: back.n, bytes: fs.statSync(copyPath).size};
    await shot(page, 'imported-copy');
    await page.close();

    /* ---- dark, and a view-only file: Inspect and Export still work, nothing can be changed ---- */
    step('dark, and a view-only file: Inspect and Export still work, n');
    const dark = await newPage({colorScheme: 'dark'}); await dark.goto(base + '#/f/f1'); await mounted(dark); await dark.waitForTimeout(300);
    await dark.evaluate(id => { HD.sel.set([id]); HD.render.zoomToFit([HD.store.parent(id)]); }, card.ids.card); await dark.waitForTimeout(300);
    await dark.locator('.hd-right section[aria-label="Export"]').scrollIntoViewIfNeeded(); await dark.waitForFunction(() => { const c = document.querySelector('.hdx-prevcv'); return c && c.width > 10; }, null, {timeout: 5000});
    eq(await layout(dark), [], 'layout with the Export section, dark'); await shot(dark, 'export-section-dark');
    await dark.locator('.hd-right .hd-tab', {hasText: 'Inspect'}).click(); await dark.waitForSelector('.hdx-code'); eq(await layout(dark), [], 'layout with the Inspect tab, dark'); await shot(dark, 'inspect-dark');
    await dark.locator('.hd-top button[title^="Export"]').click(); await dark.waitForSelector('.hdx-dialog'); await shot(dark, 'export-dialog-dark'); await dark.keyboard.press('Escape'); await dark.close();

    mock.server.viewOnly = true;
    const v = await newPage(); await v.goto(base + '#/f/f1'); await mounted(v); await v.waitForTimeout(300);
    eq(await v.evaluate(() => HD.app.file.role), 'view'); await v.evaluate(id => HD.sel.set([id]), card.ids.card);
    await v.locator('.hd-right .hd-tab', {hasText: 'Inspect'}).click(); await v.waitForSelector('.hdx-code'); ok((await v.locator('.hdx-code').textContent()).length > 50, 'view only: the Inspect tab is there, with code');
    ok(await v.locator('.hdx-inspect .hd-segb', {hasText: 'CSS'}).isEnabled(), 'and its switches work'); await v.locator('.hdx-inspect .hd-segb', {hasText: 'CSS'}).click(); await v.waitForFunction(() => /^\/\* Card \*\//.test(document.querySelector('.hdx-code').textContent));
    const vn = await v.evaluate(async () => { const n0 = HD.store.count(), r = await HD.handoff.renderOne('9:1', {fmt: 'png', scale: 1}), imp = await HD.handoff.importSvg('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>', {x: 0, y: 0}), pics = await HD.handoff.importImages([new File([new Uint8Array([1, 2, 3])], 'x.png')], null); return [r.w, r.h, imp, pics.length, HD.store.count() === n0]; });
    eq(vn, [1080, 1080, null, 0, true], 'view only: export works, import changes nothing');
    await v.evaluate(() => { HD.ui.state.rightTab = 'design'; HD.ui.state.sig = ''; HD.ui.refresh(); HD.sel.set(['9:1']); }); await v.waitForSelector('.hdx-go');
    ok(await v.locator('.hdx-row .hdx-fmt').first().isDisabled(), 'view only: the export rows can be read, not changed'); eq(await v.locator('.hdx-add').count(), 0);
    [dl] = await Promise.all([v.waitForEvent('download'), v.locator('.hdx-go').click()]); eq(dl.suggestedFilename(), 'Post 1080.zip', 'view only: the Export button still exports');
    eq(await layout(v), [], 'layout, view only'); await shot(v, 'view-only'); await v.close();

    eq(errors, [], 'no script errors');
    console.log('design_export_test: ok, ' + report.checks + ' checks');
    console.log(JSON.stringify(report));
  } catch (e) {
    if (shots) for (const c of browser.contexts()) for (const pg of c.pages()) { try { await pg.screenshot({path: path.join(shots, 'FAILED.png')}); } catch (e2) { /* closed */ } }
    throw e;
  } finally { await browser.close().catch(() => {}); await mock.close(); }
}
if (require.main === module) main().catch(e => { console.error(e); process.exit(1); });
